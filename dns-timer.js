const dns = require('dns');
const { performance } = require('perf_hooks');

function measureDNSQueryTime(domain, dnsServer = null) {
    return new Promise((resolve, reject) => {
        // Create a custom resolver if DNS server is specified
        const resolver = dnsServer ? new dns.Resolver() : dns.promises;
        
        // Configure custom DNS server if provided
        if (dnsServer) {
            resolver.setServers([dnsServer]);
        }
        
        const startTime = performance.now();

        // Use resolve4 from either the custom resolver or default dns
        const queryFunction = dnsServer ? 
            (domain, callback) => resolver.resolve4(domain, callback) :
            dns.resolve4;

        queryFunction(domain, (err, addresses) => {
            const endTime = performance.now();
            
            if (err) {
                reject({
                    error: err,
                    duration: endTime - startTime,
                    dnsServer: dnsServer || 'default'
                });
            } else {
                resolve({
                    addresses: addresses,
                    duration: endTime - startTime,
                    dnsServer: dnsServer || 'default'
                });
            }
        });
    });
}

// Example usage
async function main() {
    try {
        const domains = ['google.com', 'github.com', 'anilist.co', 'cloudflare.com'];
        const dnsServers = [
            null,                    // Default system DNS
            '8.8.8.8',              // Google DNS
            '1.1.1.1',              // Cloudflare DNS
        ];
        
        console.log('Starting DNS query measurements...\n');
        
        for (const domain of domains) {
            console.log(`Domain: ${domain}`);
            
            for (const server of dnsServers) {
                const serverName = server || 'Default DNS';
                console.log(`\nTesting with ${serverName}...`);
                
                try {
                    const result = await measureDNSQueryTime(domain, server);
                    console.log(`├─ IP Addresses: ${result.addresses.join(', ')}`);
                    console.log(`└─ Query time: ${result.duration.toFixed(2)}ms`);
                } catch (error) {
                    console.error(`├─ Error: ${error.error.message}`);
                    console.log(`└─ Query failed after ${error.duration.toFixed(2)}ms`);
                }
            }
            console.log('\n' + '-'.repeat(50) + '\n');
        }
    } catch (error) {
        console.error('Fatal error:', error);
    }
}

main();