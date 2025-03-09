import random, os, sys, subprocess

def generate_random_numbers(input_count, min_val, max_val):
    if min_val > max_val:
        raise ValueError("min_val should be less than or equal to max_val.")
    random_numbers = [random.randint(min_val, max_val) for _ in range(input_count)]
    return random_numbers

def run_code(correct_code_file, input_data):

    if not os.path.exists(correct_code_file):
        print(f"Error: {correct_code_file} does not exist at the specified path.")
        return ""
    
    file_extension = os.path.splitext(correct_code_file)[1].lower()

    if file_extension == ".py":
        print(f"Running Python script {correct_code_file} with input: {input_data}")
        result = subprocess.run(
            [sys.executable, correct_code_file], input=input_data, text=True, capture_output=True
        )
        return result.stdout.strip()
    
    elif file_extension == ".c":
        print(f"Compiling C code {correct_code_file} and running with input: {input_data}")
        # Compile the C code
        executable = "program"
        compile_result = subprocess.run(
            ["gcc", correct_code_file, "-o", executable], capture_output=True, text=True
        )
        
        if compile_result.returncode != 0:
            print(f"Compilation error: {compile_result.stderr}")
            return ""
        
        # Run the compiled C executable
        result = subprocess.run(
            [f"./{executable}"], input=input_data, text=True, capture_output=True
        )
        return result.stdout.strip()

    elif file_extension == ".cpp":
        print(f"Compiling C++ code {correct_code_file} and running with input: {input_data}")
        # Compile the C++ code
        executable = "program_cpp"
        compile_result = subprocess.run(
            ["g++", correct_code_file, "-o", executable], capture_output=True, text=True
        )
        
        if compile_result.returncode != 0:
            print(f"Compilation error: {compile_result.stderr}")
            return ""
        
        # Run the compiled C++ executable
        result = subprocess.run(
            [f"./{executable}"], input=input_data, text=True, capture_output=True
        )
        return result.stdout.strip()

    else:
        print("Unsupported file type.")
        return ""
    
# Modify these variables as needed
min_val = 1     
max_val = 100   
input_count = 3
file_name = "correct.cpp"  

random_numbers = generate_random_numbers(input_count, min_val, max_val)

input_data = ' '.join(map(str, random_numbers))

print(f"Generated input: {input_data}")

correct_code_file = f"Simple_Generator/{file_name}"  # Change this to a C or C++ file as needed
actual_output = run_code(correct_code_file, input_data)

print(f"Output from the correct code: {actual_output}")
