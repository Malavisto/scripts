import random

def flip_coin(times):
    heads_count = 0
    tails_count = 0

    for _ in range(times):
        flip = random.choice(['Heads', 'Tails'])
        if flip == 'Heads':
            heads_count += 1
        else:
            tails_count += 1

    return heads_count, tails_count

# Flip the coin 100 times
times = 100
heads, tails = flip_coin(times)

# Output the results
print(f"Total flips: {times}")
print(f"Heads: {heads}")
print(f"Tails: {tails}")
