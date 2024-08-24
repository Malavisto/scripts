import cupy as cp

def flip_coin_gpu(times):
    # Generate random integers (0 or 1) on the GPU
    flips = cp.random.randint(0, 2, size=times)

    # Count heads (1) and tails (0)
    heads_count = cp.sum(flips)
    tails_count = times - heads_count

    return int(heads_count), int(tails_count)

def parallel_flip_gpu(total_flips, workers=4):
    flips_per_worker = total_flips // workers
    try:
        results = [flip_coin_gpu(flips_per_worker) for _ in range(workers)]
        
        total_heads = sum(result[0] for result in results)
        total_tails = sum(result[1] for result in results)
        
        return total_heads, total_tails

    except KeyboardInterrupt:
        print("Execution interrupted by user. Shutting down workers...")
        raise  # Re-raise the exception to exit the script

# Run the parallel coin flips on GPU
total_flips = 1000000000  # Use a large number to see the GPU advantage
workers = 4

try:
    heads, tails = parallel_flip_gpu(total_flips, workers)

    # Output the results
    print(f"Total flips: {total_flips}")
    print(f"Heads: {heads}")
    print(f"Tails: {tails}")

except KeyboardInterrupt:
    print("Script terminated by user.")
