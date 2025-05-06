from transformers import (
    MT5Tokenizer,
    MT5ForConditionalGeneration,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
    DataCollatorForSeq2Seq
)
import pandas as pd
from datasets import Dataset
import torch
df = pd.read_csv("/kaggle/input/emojivstarget/mt5_training_data.csv")
df = df.dropna(subset=["input_text", "target_text"])
final_df = df[["input_text", "target_text"]]
final_df.to_csv("/kaggle/working/final_emoji_translation_dataset.csv", index=False)
print("✅ Final dataset is ready with", len(final_df), "samples.")

emoji_ds = Dataset.from_pandas(final_df)
emoji_ds = emoji_ds.train_test_split(test_size=0.2)
model_name = "google/mt5-base"  # Changed to smaller model
tokenizer = MT5Tokenizer.from_pretrained(model_name)
model = MT5ForConditionalGeneration.from_pretrained(model_name)
max_input_length = 32 
max_target_length = 64 

def preprocess_function(example):
    model_inputs = tokenizer(
        example["input_text"], max_length=max_input_length, padding="max_length", truncation=True
    )
    with tokenizer.as_target_tokenizer():
        labels = tokenizer(
            example["target_text"], max_length=max_target_length, padding="max_length", truncation=True
        )
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs
tokenized_ds = emoji_ds.map(preprocess_function, batched=True)
training_args = Seq2SeqTrainingArguments(
    output_dir="/kaggle/working/mt5-emoji-model",
    do_eval=True,
    save_strategy="epoch",
    eval_strategy="epoch",
    learning_rate=5e-5,
    per_device_train_batch_size=1,  
    per_device_eval_batch_size=1,   
    gradient_accumulation_steps=8,  
    weight_decay=0.01,
    save_total_limit=2,
    num_train_epochs=3,
    fp16=True,
    logging_dir="/kaggle/working/logs",
    load_best_model_at_end=True,
    metric_for_best_model="loss",
    report_to="none",
    gradient_checkpointing=True,
    fp16_full_eval=True,
)

data_collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model)

trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_ds["train"],
    eval_dataset=tokenized_ds["test"],
    tokenizer=tokenizer,
    data_collator=data_collator,
)

print("🚀 Training started...")
trainer.train()
trainer.save_model("/kaggle/working/mt5-emoji-model-final")
tokenizer.save_pretrained("/kaggle/working/mt5-emoji-model-final")
