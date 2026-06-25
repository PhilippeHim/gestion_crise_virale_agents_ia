# Importations

import re
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import EDA

# Fonctions

def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""

    text = text.lower()
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"@\w+", "@user", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text

def normalize_column(df, col):
    df = df.copy()
    df["text_norm"] = df[col].astype(str).str.lower()
    df["text_norm"] = df["text_norm"].str.replace(r"https?://\S+|www\.\S+", "", regex=True)
    df["text_norm"] = df["text_norm"].str.replace(r"@\w+", "@user", regex=True)
    df["text_norm"] = df["text_norm"].str.replace(r"\s+", " ", regex=True).str.strip()
    return df

def assign_tone(text: str, sentiment: str) -> int:
    text = text.lower()

    # =========================
    # 😡 AGRESSIF (priorité haute)
    # =========================
    if any(w in text for w in [
        "nul", "dégage", "incompétent", "honte", "ridicule", "stupide", "arnaque"
    ]):
        return 3

    # =========================
    # 🧠 CRITIQUE (constructif négatif)
    # =========================
    if sentiment == "negative" and any(w in text for w in [
        "mais", "cependant", "problème", "dommage", "toutefois", "améliorer"
    ]):
        return 2

    # =========================
    # 😄 ENTHOUSIASTE
    # =========================
    if any(w in text for w in [
        "super", "génial", "incroyable", "excellent", "parfait", "😍", "🔥"
    ]):
        return 0

    # =========================
    # 📢 INFORMATIF
    # =========================
    if any(w in text for w in [
        "info", "mise à jour", "selon", "rapport", "résultat", "données", "publication"
    ]):
        return 1

    # =========================
    # 😂 IRONIQUE (optionnel)
    # =========================
    if "..." in text or "🙄" in text or "bien sûr" in text:
        return 5

    # =========================
    # 😐 NEUTRE DEFAULT
    # =========================
    return 4

def build_labels(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["tone"] = df.apply(
        lambda row: assign_tone(
            row["text_norm"],
            row["Sentiment"]
        ),
        axis=1
    )

    return df

def tokenize_batch(texts, max_len=128):
    return tokenizer(
        list(texts),
        truncation=True,
        padding=True,
        max_length=max_len
    )

def prepare_dataset(df, tokenizer, model, device):

    # 1. clean vectorisé
    df = normalize_column(df, "Full Text")

    # 2. sentiment GPU
    texts = df["text_norm"].tolist()

    df["sentiment_pred"] = predict_sentiment(
        texts, tokenizer, model, device
    )

    # 3. mapping sentiment
    label_map = {0: "negative", 1: "neutral", 2: "positive"}
    df["sentiment_label"] = df["sentiment_pred"].map(label_map)

    # 4. tone rule-based (rapide CPU OK)
    df["tone"] = [
        assign_tone(t, s)
        for t, s in zip(df["text_norm"], df["Sentiment"])
    ]

    return df

def predict_sentiment(texts, tokenizer, model, device, batch_size=64):
    results = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]

        enc = tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=128,
            return_tensors="pt"
        ).to(device)

        with torch.no_grad():
            outputs = model(**enc)
            preds = torch.argmax(outputs.logits, dim=1)

        results.extend(preds.cpu().numpy())

    return results

# Tests

if __name__ == "__main__":

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        use_fast=False
    )

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME
    ).to(device)

    model.eval()

    df = EDA.lecture_excel_dataset(dataset_path='data/data.xlsx')

    # df_sample = df.sample(1000, random_state=42)
    df_sample = df

    df_ready = prepare_dataset(df_sample, tokenizer, model, device)

    tone_map = {
        0: "enthousiaste",
        1: "informatif",
        2: "critique",
        3: "agressif",
        4: "neutre",
        5: "ironique"
    }

    df_ready["tone_label"] = df_ready["tone"].map(tone_map)

    print(df_ready.head())

    df_ready.to_excel("df_tonalite.xlsx", index=False)