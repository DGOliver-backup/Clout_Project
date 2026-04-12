import os
import random
import string

#Create the data folder
output_dir = "test_data"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

#Write Charactors in blocks
def generate_random_file(filename, size_kb):
    filepath = os.path.join(output_dir, filename)
    chars = string.ascii_letters + string.digits + " "
    with open(filepath, 'w') as f:
        for _ in range(size_kb):
            content = ''.join(random.choices(chars, k=1024))
            f.write(content)

#Generate small, medium and large files
for i in range(1, 51):
    size = random.randint(1, 10)
    generate_random_file(f"small{i}.txt", size)

for i in range(1, 41):
    size = random.randint(100, 500)
    generate_random_file(f"medium{i}.txt", size)

for i in range(1, 31):
    size = random.randint(1024, 11 * 1024) 
    generate_random_file(f"large{i}.txt", size)

print("\nGeneration Completed")