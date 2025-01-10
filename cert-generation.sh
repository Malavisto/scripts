#!/bin/bash

# Array of hostnames
HOSTS=("masungulo" "hpserver" "MASUNGULOV2")

for HOST in "${HOSTS[@]}"; do
    echo "Generating certificates for $HOST..."
    
    # Create directory for each host
    mkdir -p "${HOST}_certs"
    cd "${HOST}_certs"

    # Generate private key
    openssl genrsa -out node_exporter.key 2048

    # Generate config file for certificate
    cat > openssl.cnf << EOF
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
C = ZA
ST = State
L = Location
O = Organization
OU = Monitoring
CN = $HOST

[v3_req]
keyUsage = keyEncipherment, dataEncipherment, digitalSignature
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = $HOST
DNS.2 = $HOST.local
IP.1 = 127.0.0.1
EOF

    # Generate certificate
    openssl req -new -x509 -key node_exporter.key -out node_exporter.crt -days 3650 -config openssl.cnf

    # Generate web config file for node_exporter
    cat > web-config.yml << EOF
tls_server_config:
  cert_file: node_exporter.crt
  key_file: node_exporter.key
EOF

    cd ..
    echo "Certificates generated for $HOST"
    echo "----------------------------------------"
done

echo "All certificates have been generated!"
