const dns = require('dns');
const { performance } = require('perf_hooks');

function measureDNSQueryTime(domain) {
    return new Promise((resolve, reject) => {
        const startTime = performance.now();

        dns.resolve4(domain, (err, addresses) => {
            const endTime = performance.now();
            
            if (err) {
                reject({
                    error: err,
                    duration: endTime - startTime
                });
            } else {
                resolve({
                    addresses: addresses,
                    duration: endTime - startTime
                });
            }
        });
    });
}

// Example usage
async function main() {
    try {
        const domains = ['google.com', 'github.com', 'malavisto.co.za'];
        
        console.log('Starting DNS query measurements...\n');
        
        for (const domain of domains) {
            console.log(`Querying ${domain}...`);
            const result = await measureDNSQueryTime(domain);
            console.log(`├─ IP Addresses: ${result.addresses.join(', ')}`);
            console.log(`└─ Query time: ${result.duration.toFixed(2)}ms\n`);
        }
    } catch (error) {
        console.error('Error:', error.error.message);
        console.log(`Query failed after ${error.duration.toFixed(2)}ms`);
    }
}

main();