import subprocess

def parse_upsc_output(output):
    # Create a dictionary to store the parsed information
    data = {}
    
    # Split the output into lines
    lines = output.splitlines()
    
    # Iterate through the lines and extract key-value pairs
    for line in lines:
        if line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    
    return data

def display_basic_info(data):
    # Display basic UPS info
    print("UPS Basic Information:")
    print(f"Battery Charge: {data.get('battery.charge', 'N/A')}%")
    print(f"Battery Voltage: {data.get('battery.voltage', 'N/A')}V")
    print(f"Input Voltage: {data.get('input.voltage', 'N/A')}V")
    print(f"Output Voltage: {data.get('output.voltage', 'N/A')}V")
    print(f"UPS Status: {data.get('ups.status', 'N/A')}")
    print(f"UPS Load: {data.get('ups.load', 'N/A')}")
    print(f"UPS Type: {data.get('ups.type', 'N/A')}")
    print(f"Driver Version: {data.get('driver.version', 'N/A')}")

def get_upsc_data():
    # Run the `upsc nutdev1` command and get the output
    try:
        result = subprocess.run(['upsc', 'nutdev1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
        output = result.stdout
        return output
    except subprocess.CalledProcessError as e:
        print(f"Error running upsc: {e}")
        return None

def main():
    # Get the data from the UPS
    output = get_upsc_data()
    
    if output:
        # Parse the output
        data = parse_upsc_output(output)
        
        # Display the basic info
        display_basic_info(data)

if __name__ == "__main__":
    main()
