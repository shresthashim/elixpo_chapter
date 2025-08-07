import torch
if torch.cuda.is_available():
    device = torch.device("cuda:0")
    print(f"✅ Using GPU: {torch.cuda.get_device_name(device)}")
else:
    device = torch.device("cpu")
    print("⚠️ CUDA not available, using CPU instead.")