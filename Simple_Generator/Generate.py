import random , os , sys
import subprocess

def generate_random_numbers(input_count, min_val, max_val):
    if min_val > max_val:
        raise ValueError("min_val should be less than or equal to max_val.")
    
    random_numbers = [random.randint(min_val, max_val) for _ in range(input_count)]
    return random_numbers

def run_code(correct_code_file, input_data):
    """
    Runs the correct code and captures the output.
    """

    if not os.path.exists(correct_code_file):
        print(f"Error: {correct_code_file} does not exist at the specified path.")
        return ""
    

    print(f"Running {correct_code_file} with input: {input_data}") 
    

    result = subprocess.run(
        [sys.executable, correct_code_file], input=input_data, text=True, capture_output=True
    )
    return result.stdout.strip()

min_val = 1     
max_val = 100   
input_count = 2
correct_code_file = "Simple_Generator/correct.py" 

random_numbers = generate_random_numbers(input_count, min_val, max_val)

input_data = ' '.join(map(str, random_numbers))

print(f"Generated input: {input_data}")

actual_output = run_code(correct_code_file, input_data)

print(f"Output from the correct code: {actual_output}")
