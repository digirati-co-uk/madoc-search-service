import csv
import sys

def read_csv(filename):
    data = {}
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data[row['Profile']] = {k: float(v) for k, v in row.items() if k != 'Profile'}
    return data

def main(baseline_file, optimized_file):
    baseline = read_csv(baseline_file)
    optimized = read_csv(optimized_file)
    
    print("| Profile | Baseline Mean | Optimized Mean | Improvement |")
    print("|---|---|---|---|")
    
    for profile in baseline:
        b_mean = baseline[profile]['Mean']
        o_mean = optimized[profile]['Mean']
        improvement = ((b_mean - o_mean) / b_mean) * 100
        
        print(f"| {profile} | {b_mean:.2f}ms | {o_mean:.2f}ms | {improvement:.2f}% |")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python compare.py baseline.csv optimized.csv")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
