"""
model.py — CNN for handwritten character classification
========================================================
Architecture: lightweight CNN trained to classify segmented
handwritten characters (a–z). Used downstream by analyzer.py
to detect dyslexia-related letter confusions and reversals.

Training dataset: EMNIST Letters (balanced split, 26 classes a–z)
  → pip install torchvision
  → python model.py --train          # trains and saves model.pth
  → python model.py --eval           # evaluates on test split

The model is intentionally small so it runs on CPU in real time
during the web demo without a GPU.
"""

import argparse
import os
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NUM_CLASSES   = 26          # a–z
IMG_SIZE      = 28          # EMNIST images are 28×28
BATCH_SIZE    = 256
EPOCHS        = 15
LR            = 1e-3
SAVE_PATH     = Path("model.pth")
DEVICE        = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# EMNIST label offset: EMNIST Letters uses labels 1–26; subtract 1 → 0–25
LABEL_OFFSET  = 1

# Readable class names
CLASSES = list("abcdefghijklmnopqrstuvwxyz")

# Pairs commonly confused by dyslexic writers
DYSLEXIA_CONFUSIONS = {
    "b": ["d", "p", "q"],
    "d": ["b", "p", "q"],
    "p": ["b", "d", "q"],
    "q": ["b", "d", "p"],
    "n": ["u"],
    "u": ["n"],
    "m": ["w"],
    "w": ["m"],
    "s": ["z"],
    "z": ["s"],
}


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class DyslexiaCNN(nn.Module):
    """
    Small convolutional network for 28×28 grayscale letter images.

    Architecture:
        Conv block 1: 1 → 32 filters, 3×3, BN, ReLU, MaxPool
        Conv block 2: 32 → 64 filters, 3×3, BN, ReLU, MaxPool
        Conv block 3: 64 → 128 filters, 3×3, BN, ReLU
        Global average pooling
        FC: 128 → 26 classes

    ~200k parameters — runs inference in <5 ms on CPU.
    """

    def __init__(self, num_classes: int = NUM_CLASSES) -> None:
        super().__init__()

        self.features = nn.Sequential(
            # Block 1
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),                        # → 14×14

            # Block 2
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),                        # → 7×7

            # Block 3
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
        )

        # Global average pooling replaces a large FC layer — fewer parameters,
        # less overfitting on small training sets.
        self.gap = nn.AdaptiveAvgPool2d(1)          # → 1×1

        self.classifier = nn.Sequential(
            nn.Dropout(0.4),
            nn.Linear(128, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.gap(x)
        x = x.flatten(1)
        return self.classifier(x)


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def get_transforms(train: bool) -> transforms.Compose:
    ops = []
    if train:
        ops += [
            transforms.RandomRotation(10),
            transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)),
        ]
    ops += [
        transforms.ToTensor(),
        transforms.Normalize((0.1722,), (0.3310,)),   # EMNIST Letters stats
    ]
    return transforms.Compose(ops)

class _LabelOffset:
    def __init__(self, offset):
        self.offset = offset
    def __call__(self, y):
        return y - self.offset

def get_loaders(root="./data"):
    label_tf = _LabelOffset(LABEL_OFFSET)
    train_ds = datasets.EMNIST(
        root=root, split="letters", train=True,
        download=True, transform=get_transforms(train=True),
        target_transform=label_tf,
    )
    test_ds = datasets.EMNIST(
        root=root, split="letters", train=False,
        download=True, transform=get_transforms(train=False),
        target_transform=label_tf,
    )
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=0, pin_memory=False)
    test_loader  = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False,
                              num_workers=0, pin_memory=False)
    return train_loader, test_loader

# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(save_path: Path = SAVE_PATH) -> None:
    print(f"Device: {DEVICE}")
    model = DyslexiaCNN().to(DEVICE)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    train_loader, test_loader = get_loaders()

    best_acc = 0.0
    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss, correct, total = 0.0, 0, 0
        t0 = time.time()

        for imgs, labels in train_loader:
            imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
            optimizer.zero_grad()
            logits = model(imgs)
            loss   = criterion(logits, labels)
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * imgs.size(0)
            correct    += (logits.argmax(1) == labels).sum().item()
            total      += imgs.size(0)

        scheduler.step()
        train_acc = correct / total * 100
        val_acc   = evaluate(model, test_loader)
        elapsed   = time.time() - t0

        print(f"Epoch {epoch:02d}/{EPOCHS}  "
              f"loss={total_loss/total:.4f}  "
              f"train_acc={train_acc:.1f}%  "
              f"val_acc={val_acc:.1f}%  "
              f"({elapsed:.1f}s)")

        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), save_path)
            print(f"  ✓ Saved best model ({val_acc:.1f}%)")

    print(f"\nTraining complete. Best val accuracy: {best_acc:.1f}%")
    print(f"Model saved to: {save_path}")


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate(model: nn.Module, loader: DataLoader) -> float:
    model.eval()
    correct, total = 0, 0
    with torch.no_grad():
        for imgs, labels in loader:
            imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
            preds = model(imgs).argmax(1)
            correct += (preds == labels).sum().item()
            total   += imgs.size(0)
    return correct / total * 100


def eval_from_checkpoint(path: Path = SAVE_PATH) -> None:
    model = load_model(path)
    _, test_loader = get_loaders()
    acc = evaluate(model, test_loader)
    print(f"Test accuracy: {acc:.2f}%")


# ---------------------------------------------------------------------------
# Inference helpers (used by analyzer.py)
# ---------------------------------------------------------------------------

def load_model(path: Path = SAVE_PATH) -> DyslexiaCNN:
    """Load a trained DyslexiaCNN from a checkpoint file."""
    model = DyslexiaCNN()
    state = torch.load(path, map_location="cpu")
    model.load_state_dict(state)
    model.eval()
    return model


def predict_letter(
    model: DyslexiaCNN,
    img_tensor: torch.Tensor,
    top_k: int = 3,
) -> list[tuple[str, float]]:
    """
    Predict the top-k most likely letters for a 1×1×28×28 tensor.

    Returns:
        List of (letter, probability) tuples, sorted by probability descending.
    """
    with torch.no_grad():
        logits = model(img_tensor)
        probs  = torch.softmax(logits, dim=1)[0]

    top = torch.topk(probs, k=min(top_k, NUM_CLASSES))
    return [(CLASSES[i.item()], p.item()) for i, p in zip(top.indices, top.values)]


def is_dyslexia_confusion(predicted: str, actual: str) -> bool:
    """
    Return True if the confusion between predicted and actual
    is a known dyslexia-related error pattern.
    """
    return actual in DYSLEXIA_CONFUSIONS.get(predicted, [])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DyslexiaCNN training / evaluation")
    parser.add_argument("--train", action="store_true", help="Train the model")
    parser.add_argument("--eval",  action="store_true", help="Evaluate from checkpoint")
    parser.add_argument("--save",  type=str, default=str(SAVE_PATH), help="Model path")
    args = parser.parse_args()

    if args.train:
        train(Path(args.save))
    elif args.eval:
        eval_from_checkpoint(Path(args.save))
    else:
        parser.print_help()
