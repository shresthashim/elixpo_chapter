from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# Load the fine-tuned model and tokenizer from Hugging Face Hub
model_name = "treysarkar/t5email_base_v2"  # Your model name
tokenizer = AutoTokenizer.from_pretrained("t5-base")
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

# Define the function for generating email outputs
def generate_email(prompt, model, tokenizer, max_length=512):
    # Tokenize the input prompt
    inputs = tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
    
    # Generate the output
    outputs = model.generate(
        inputs.input_ids, 
        max_length=max_length, 
        num_beams=5,  # Use beam search for better results
        early_stopping=True
    )
    
    # Decode and return the generated text
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

# List of example prompts
prompts = [
    " Doctor Visited: Dr. Radhika Verma, Age: 34,Patient: Aditi Sharma, Symptoms: Fever, Cough, Headache, Medicines Suggested: Paracetamol, Address: 89 Green Lane, Last Checkup Date: 2023-11-12. Generate a professional email based on this information.",
    # "Patient: Arun Singh, Age: 25, Symptoms: Nausea, Vomiting, Medicines Suggested: Ondansetron, Doctor Visited: Dr. Neha Agarwal, Address: 45 Red Street, Last Checkup Date: 2023-10-30. Generate a professional email based on this information.",
    # "Patient Name: Priya Mehta, Age: 28, Symptoms: Fatigue, Joint Pain, Medicines Suggested: Ibuprofen, Doctor Visited: Dr. Sudhir Kumar, Address: 21 Whitefield Avenue, Last Checkup Date: 2023-09-20. Generate a professional email based on this information.",
    # "Patient: Rajesh Kumar, Age: 41, Symptoms: Chest Pain, Difficulty Breathing, Medicines Suggested: Aspirin, Doctor Visited: Dr. Shalini Gupta, Address: 78 Park Road, Last Checkup Date: 2023-11-05. Generate a professional email based on this information.",
    # "Patient Name: Sunita Yadav, Age: 30, Symptoms: Back Pain, Dizziness, Medicines Suggested: Tylenol, Doctor Visited: Dr. Vikram Singh, Address: 67 Blue Ridge, Last Checkup Date: 2023-12-01. Generate a professional email based on this information."
    # "Patient Name: Sunita Yadav, Age: 30, Symptoms: Back Pain, Dizziness, Medicines Suggested: Tylenol, Doctor Visited: Dr. Vikram Singh, Address: 67 Blue Ridge, Last Checkup Date: 2023-12-01. Generate a professional email based on this information."
    "My name is Rajesh Mukho, my age is 34, symptoms are skin rashes, medicines are duphalac, doctor visited was Dr. Raghuram De, addres: 12 Nilgunj, last checkup on 23-03-23. Write an email to the doctor"
]

# Generate and print emails for each prompt
for i, prompt in enumerate(prompts):
    email = generate_email(prompt, model, tokenizer)
    print(f"Prompt {i+1}:\n{prompt}\nGenerated Email:\n{email}\n{'-'*50}")