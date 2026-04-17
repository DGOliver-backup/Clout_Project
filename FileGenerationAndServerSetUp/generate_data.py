import os
import random
import string

output_dir = "test_data"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

base_1kb_chunk = ''.join(random.choices(string.ascii_letters + string.digits + " ", k=1024))

def generate_random_file(filename, size_kb):
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w') as f:
        for _ in range(size_kb):
            f.write(base_1kb_chunk)
    print(f"Generated: {filename} ({size_kb} KB)")

TARGET_TOTAL_MB = 200
TARGET_TOTAL_KB = TARGET_TOTAL_MB * 1024  # 204800 KB
current_total_kb = 0


# 200 Files in total, 200MB

# 1. Write 400 small files (1 KB - 10 KB)
for i in range(1, 111):
    size = random.randint(1, 10)
    generate_random_file(f"small{i}.txt", size)
    current_total_kb += size

# 2. Write 80 medium files (100 KB - 500 KB)
for i in range(1, 71):
    size = random.randint(100, 500)
    generate_random_file(f"medium{i}.txt", size)
    current_total_kb += size

# 3. Write 20 large files (Balance the rest to hit exactly 200MB)
for i in range(1, 21):
    if i == 20:
        # Last file take all space remaining
        size = TARGET_TOTAL_KB - current_total_kb
    else:
        # Random size for first 19 files
        size = random.randint(5 * 1024, 10 * 1024)

    generate_random_file(f"large{i}.txt", size)
    current_total_kb += size

print("\nGeneration Completed")
