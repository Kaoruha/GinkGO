
import subprocess
result = subprocess.run(['which', 'python'], capture_output=True, text=True)
print(result.stdout.strip())
