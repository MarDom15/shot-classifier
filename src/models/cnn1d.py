"""Petit reseau de neurones convolutif 1D pour classifier directement les
512 echantillons bruts (sans extraction de caracteristiques manuelle).

Volontairement compact (peu de parametres, dropout) car le jeu de donnees
est petit (quelques centaines d'exemples) : un CNN profond memoriserait le
train sans generaliser.
"""
from __future__ import annotations

from torch import nn


class Shot1DCNN(nn.Module):
    def __init__(self, n_classes: int, in_len: int = 512, dropout: float = 0.3):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv1d(1, 16, kernel_size=9, padding=4),
            nn.BatchNorm1d(16),
            nn.ReLU(),
            nn.MaxPool1d(4),  # 512 -> 128

            nn.Conv1d(16, 32, kernel_size=7, padding=3),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.MaxPool1d(4),  # 128 -> 32

            nn.Conv1d(32, 64, kernel_size=5, padding=2),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(1),  # global average pooling -> 64
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(dropout),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, n_classes),
        )

    def forward(self, x):
        # x: (batch, in_len) -> (batch, 1, in_len)
        x = x.unsqueeze(1)
        x = self.features(x)
        return self.classifier(x)
