import os
import time
import random
import argparse

def write_test(file_path, file_size_mb):
    file_size = file_size_mb * 1024 * 1024
    data = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=file_size))
    
    start_time = time.time()
    with open(file_path, 'w') as f:
        f.write(data)
    end_time = time.time()
    
    write_speed = file_size_mb / (end_time - start_time)
    return write_speed

def read_test(file_path):
    start_time = time.time()
    with open(file_path, 'r') as f:
        data = f.read()
    end_time = time.time()
    
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    read_speed = file_size_mb / (end_time - start_time)
    return read_speed

def run_test(mount_point, file_size_mb, num_runs):
    file_path = os.path.join(mount_point, 'test_file.txt')
    write_speeds = []
    read_speeds = []

    for i in range(num_runs):
        print(f"Run {i+1}/{num_runs}")
        
        write_speed = write_test(file_path, file_size_mb)
        write_speeds.append(write_speed)
        print(f"  Write speed: {write_speed:.2f} MB/s")
        
        read_speed = read_test(file_path)
        read_speeds.append(read_speed)
        print(f"  Read speed: {read_speed:.2f} MB/s")
        
        # Clean up
        os.remove(file_path)

    avg_write_speed = sum(write_speeds) / num_runs
    avg_read_speed = sum(read_speeds) / num_runs

    print("\nAverage speeds:")
    print(f"  Write: {avg_write_speed:.2f} MB/s")
    print(f"  Read: {avg_read_speed:.2f} MB/s")

def main():
    parser = argparse.ArgumentParser(description="Test disk read/write speeds")
    parser.add_argument("mount_point", help="Mount point to test (e.g., /mnt/mydisk)")
    parser.add_argument("--size", type=int, default=100, help="Size of test file in MB (default: 100)")
    parser.add_argument("--runs", type=int, default=5, help="Number of test runs (default: 5)")
    args = parser.parse_args()

    if not os.path.exists(args.mount_point):
        print(f"Error: Mount point {args.mount_point} does not exist.")
        return

    print(f"Testing with a {args.size} MB file on {args.mount_point}")
    print(f"Running {args.runs} tests\n")

    run_test(args.mount_point, args.size, args.runs)

if __name__ == "__main__":
    main()
