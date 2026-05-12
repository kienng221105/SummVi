import json
import jsonlines
import torch
import numpy as np
import mlflow
from pathlib import Path
from dataclasses import dataclass
from functools import partial
from torch.optim import AdamW
from torch.cuda.amp import autocast
from torch.utils.data import DataLoader, Dataset, random_split
from transformers import (
    T5Tokenizer,
    AutoModelForSeq2SeqLM,
    get_linear_schedule_with_warmup,
)
from huggingface_hub import hf_hub_download
from rouge_score import rouge_scorer
from tqdm import tqdm
@dataclass
class TrainingConfig:
    base_model: str              = "VietAI/vit5-base-vietnews-summarization"
    resume_from: str | None       = None   
    val_split: float             = 0.1
    max_input_tokens: int        = 1024
    max_output_tokens: int       = 512
    epochs: int                  = 3
    batch_size: int              = 4
    grad_accumulation: int       = 8
    learning_rate: float         = 5e-5
    warmup_ratio: float          = 0.1
    max_grad_norm: float         = 1.0
    mixed_precision: bool        = True
    eval_every_n_steps: int      = 100
    save_every_n_steps: int      = 500
    rouge_every_n_steps: int     = 200
    val_every_n_epochs: int      = 1
    rouge_every_n_epochs: int    = 2
    rouge_max_samples: int       = 100
    early_stopping_patience: int = 3
    mlflow_experiment: str       = "summvi-vit5-kd"
    mlflow_tracking_uri: str     = "/content/drive/MyDrive/SummVi_checkpoints/mlruns"
def load_tokenizer(model_path: str) -> T5Tokenizer:
    try:
        return T5Tokenizer.from_pretrained(model_path, legacy=True)
    except Exception:
        vocab_file = hf_hub_download(
            repo_id="VietAI/vit5-base",
            filename="spiece.model",
        )
        return T5Tokenizer(vocab_file=vocab_file, legacy=True)

class KDDataset(Dataset):
    def __init__(self, path: str, level: int | None = None):
        with jsonlines.open(path) as reader:
            self.data = [
                d for d in reader
                if level is None or d.get("level") == level
            ]

    def __len__(self): return len(self.data)
    def __getitem__(self, index): return self.data[index]

def collate_fn(batch, tokenizer, max_input, max_output):
    sources = [item["source"] for item in batch]
    targets = [item["target"] for item in batch]
    inputs = tokenizer(
        sources,
        padding=True,
        truncation=True,
        max_length=max_input,
        return_tensors="pt",
    )
    labels = tokenizer(
        targets,
        padding=True,
        truncation=True,
        max_length=max_output,
        return_tensors="pt",
    ).input_ids
    labels[labels == tokenizer.pad_token_id] = -100
    return {
        "input_ids": inputs.input_ids,
        "attention_mask": inputs.attention_mask,
        "labels": labels,
    }

def compute_rouge(
    model,
    tokenizer,
    val_loader,
    device,
    max_output_tokens,
    max_samples,
) -> dict:
    scorer = rouge_scorer.RougeScorer(
        ["rouge1", "rouge2", "rougeL"], use_stemmer=False
    )
    model.eval()
    r1, r2, rl = [], [], []
    samples_seen = 0
    with torch.no_grad():
        for batch in val_loader:
            if samples_seen >= max_samples:
                break
            batch = {k: v.to(device) for k, v in batch.items()}
            output_ids = model.generate(
                input_ids=batch["input_ids"],
                attention_mask=batch["attention_mask"],
                max_new_tokens=max_output_tokens,
                num_beams=2,
            )
            preds = tokenizer.batch_decode(output_ids, skip_special_tokens=True)
            refs  = tokenizer.batch_decode(
                batch["labels"].clamp(min=0), skip_special_tokens=True
            )
            for pred, ref in zip(preds, refs):
                scores = scorer.score(ref, pred)
                r1.append(scores["rouge1"].fmeasure)
                r2.append(scores["rouge2"].fmeasure)
                rl.append(scores["rougeL"].fmeasure)
            samples_seen += len(preds)
    model.train()
    return {
        "rouge1": float(np.mean(r1)) if r1 else 0.0,
        "rouge2": float(np.mean(r2)) if r2 else 0.0,
        "rougeL": float(np.mean(rl)) if rl else 0.0,
    }

def _compute_val_loss(model, val_loader, device, use_amp) -> float:
    model.eval()
    total = 0.0
    with torch.no_grad():
        for batch in val_loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            with autocast(enabled=use_amp):
                loss = model(
                    input_ids=batch["input_ids"],
                    attention_mask=batch["attention_mask"],
                    labels=batch["labels"],
                ).loss
            total += loss.item()
    model.train()
    return total / max(len(val_loader), 1)

def train_kd(
    dataset_path: str,
    output_dir: str,
    config: TrainingConfig | None = None,
) -> dict:
    config = config or TrainingConfig()
    device  = "cuda" if torch.cuda.is_available() else "cpu"
    use_amp = config.mixed_precision and device == "cuda"
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "config.json").write_text(
        json.dumps(config.__dict__, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    load_path = config.resume_from or config.base_model
    print(f"Loading from: {load_path}")

    tokenizer = load_tokenizer(load_path)
    model     = AutoModelForSeq2SeqLM.from_pretrained(load_path)
    model.to(device)
    full_dataset = KDDataset(dataset_path)
    n_val   = max(1, int(len(full_dataset) * config.val_split))
    n_train = len(full_dataset) - n_val
    train_set, val_set = random_split(
        full_dataset, [n_train, n_val],
        generator=torch.Generator().manual_seed(42),
    )
    _collate = partial(
        collate_fn,
        tokenizer=tokenizer,
        max_input=config.max_input_tokens,
        max_output=config.max_output_tokens,
    )
    use_pin      = device == "cuda"
    train_loader = DataLoader(
        train_set, batch_size=config.batch_size,
        shuffle=True, collate_fn=_collate, pin_memory=use_pin,
    )
    val_loader   = DataLoader(
        val_set, batch_size=config.batch_size,
        shuffle=False, collate_fn=_collate, pin_memory=use_pin,
    )
    optimizer    = AdamW(model.parameters(), lr=config.learning_rate)
    total_steps  = (len(train_loader) * config.epochs) // config.grad_accumulation
    warmup_steps = int(total_steps * config.warmup_ratio)
    scheduler    = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    if config.resume_from:
        opt_path = Path(config.resume_from) / "optimizer.pt"
        sch_path = Path(config.resume_from) / "scheduler.pt"
        if opt_path.exists():
            optimizer.load_state_dict(torch.load(opt_path, map_location=device))
            print("Resumed optimizer state")
        if sch_path.exists():
            scheduler.load_state_dict(torch.load(sch_path))
            print("Resumed scheduler state")
    history = {
        "config":        config.__dict__,
        "epochs":        [],
        "step_metrics":  [],
        "best_val_loss": float("inf"),
        "best_epoch":    0,
        "stopped_early": False,
        "resumed_from":  config.resume_from,
    }
    best_val_loss  = float("inf")
    step_patience  = 0
    epoch_patience = 0
    global_step    = 0
    mlflow.set_tracking_uri(config.mlflow_tracking_uri)
    mlflow.set_experiment(config.mlflow_experiment)
    with mlflow.start_run():
        mlflow.log_params({
            "base_model":        config.base_model,
            "resume_from":       config.resume_from or "none",
            "epochs":            config.epochs,
            "batch_size":        config.batch_size,
            "grad_accumulation": config.grad_accumulation,
            "learning_rate":     config.learning_rate,
            "warmup_ratio":      config.warmup_ratio,
            "mixed_precision":   config.mixed_precision,
            "train_samples":     n_train,
            "val_samples":       n_val,
        })
        for epoch in range(1, config.epochs + 1):
            model.train()
            train_loss = 0.0
            optimizer.zero_grad()
            pbar = tqdm(train_loader, desc=f"Epoch {epoch}/{config.epochs}")
            for step, batch in enumerate(pbar, 1):
                batch = {k: v.to(device) for k, v in batch.items()}
                with autocast(enabled=use_amp):
                    outputs = model(
                        input_ids=batch["input_ids"],
                        attention_mask=batch["attention_mask"],
                        labels=batch["labels"],
                    )
                    loss = outputs.loss / config.grad_accumulation
                scaled_loss = scaler.scale(loss)
                assert isinstance(scaled_loss, torch.Tensor)
                scaled_loss.backward()
                train_loss += outputs.loss.item()
                if step % config.grad_accumulation == 0:
                    scaler.unscale_(optimizer)
                    torch.nn.utils.clip_grad_norm_(
                        model.parameters(), config.max_grad_norm
                    )
                    scaler.step(optimizer)
                    scaler.update()
                    scheduler.step()
                    optimizer.zero_grad()
                    global_step += 1
                    current_lr = scheduler.get_last_lr()[0]
                    pbar.set_postfix(
                        loss=f"{outputs.loss.item():.4f}",
                        step=global_step,
                    )
                    if global_step % config.eval_every_n_steps == 0:
                        step_val_loss = _compute_val_loss(
                            model, val_loader, device, use_amp
                        )
                        step_metrics = {
                            "step":          global_step,
                            "epoch":         epoch,
                            "train_loss":    outputs.loss.item(),
                            "val_loss":      step_val_loss,
                            "learning_rate": current_lr,
                        }
                        mlflow.log_metrics({
                            "step_train_loss": outputs.loss.item(),
                            "step_val_loss":   step_val_loss,
                            "learning_rate":   current_lr,
                        }, step=global_step)
                        if global_step % config.rouge_every_n_steps == 0:
                            rouge = compute_rouge(
                                model, tokenizer, val_loader, device,
                                config.max_output_tokens,
                                config.rouge_max_samples,
                            )
                            step_metrics.update(rouge)
                            mlflow.log_metrics(rouge, step=global_step)
                        history["step_metrics"].append(step_metrics)
                        if step_val_loss < best_val_loss:
                            best_val_loss            = step_val_loss
                            history["best_val_loss"] = step_val_loss
                            history["best_epoch"]    = epoch
                            step_patience            = 0
                            model.save_pretrained(output_path / "best")
                            tokenizer.save_pretrained(output_path / "best")
                            mlflow.log_metric(
                                "best_val_loss", step_val_loss, step=global_step
                            )
                        else:
                            step_patience += 1
                    if global_step % config.save_every_n_steps == 0:
                        ckpt = output_path / f"checkpoint-{global_step}"
                        model.save_pretrained(ckpt)
                        tokenizer.save_pretrained(ckpt)
                        torch.save(optimizer.state_dict(), ckpt / "optimizer.pt")
                        torch.save(scheduler.state_dict(), ckpt / "scheduler.pt")
            if step % config.grad_accumulation != 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(
                    model.parameters(), config.max_grad_norm
                )
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad()
            avg_train_loss = train_loss / len(train_loader)
            current_lr     = scheduler.get_last_lr()[0]
            epoch_metrics  = {
                "epoch":         epoch,
                "train_loss":    avg_train_loss,
                "learning_rate": current_lr,
            }
            if epoch % config.val_every_n_epochs == 0:
                epoch_val_loss = _compute_val_loss(
                    model, val_loader, device, use_amp
                )
                epoch_metrics["val_loss"] = epoch_val_loss
                mlflow.log_metrics({
                    "epoch_train_loss": avg_train_loss,
                    "epoch_val_loss":   epoch_val_loss,
                }, step=epoch)
                if epoch % config.rouge_every_n_epochs == 0:
                    rouge = compute_rouge(
                        model, tokenizer, val_loader, device,
                        config.max_output_tokens,
                        config.rouge_max_samples,
                    )
                    epoch_metrics.update(rouge)
                    mlflow.log_metrics({
                        "epoch_rouge1": rouge["rouge1"],
                        "epoch_rouge2": rouge["rouge2"],
                        "epoch_rougeL": rouge["rougeL"],
                    }, step=epoch)
                if epoch_val_loss < best_val_loss:
                    best_val_loss            = epoch_val_loss
                    history["best_val_loss"] = epoch_val_loss
                    history["best_epoch"]    = epoch
                    epoch_patience           = 0
                    model.save_pretrained(output_path / "best")
                    tokenizer.save_pretrained(output_path / "best")
                else:
                    epoch_patience += 1
                    if epoch_patience >= config.early_stopping_patience:
                        history["stopped_early"] = True
                        history["epochs"].append(epoch_metrics)
                        break
            history["epochs"].append(epoch_metrics)
        model.save_pretrained(output_path / "final")
        tokenizer.save_pretrained(output_path / "final")
        (output_path / "training_history.json").write_text(
            json.dumps(history, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        mlflow.log_artifact(str(output_path / "training_history.json"))
        mlflow.log_artifact(str(output_path / "config.json"))
    return history

def prepare_kd_dataset(
    corpus_path: str,
    qwen_model,
    data_pipeline,
    output_path: str,
):
    with jsonlines.open(corpus_path) as reader:
        with jsonlines.open(output_path, mode="w") as writer:
            for doc in tqdm(reader, desc="Generating KD dataset"):
                ingested, processed = data_pipeline.run(doc["file_path"])
                chunk_summaries = []
                for chunk in processed.chunks:
                    label = qwen_model.generate(
                        f"Tóm tắt đoạn văn sau:\n{chunk}",
                        max_new_tokens=256,
                    )
                    chunk_summaries.append(label)
                    writer.write({
                        "source": chunk,
                        "target": label,
                        "level": 1,
                    })
                doc_label = qwen_model.generate(
                    f"Tóm tắt tài liệu sau:\n{ingested.full_text}",
                    max_new_tokens=512,
                )
                writer.write({
                    "source": "\n".join(chunk_summaries),
                    "target": doc_label,
                    "level": 2,
                })
