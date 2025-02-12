# Run Vaping in Docker

This project provides a containerized setup for running [Vaping](https://github.com/20c/vaping), a network monitoring tool that can perform ping and HTTP checks.

## Features

- Runs Vaping in an isolated Docker container
- Automatically detects and monitors your default gateway
- Pre-configured to monitor common DNS servers (Google, Cloudflare)
- HTTP monitoring of major websites
- Persistent configuration through Docker volumes
- Automatic container restart on failure

## Prerequisites

- Docker
- Basic understanding of YAML for configuration (optional)

## Quick Start

1. Clone this repository
2. Run the setup script:
```bash
./run_vaping.sh
```

This will:
- Create a default configuration in `~/.config/vaping/config.yaml`
- Build the Docker image if needed
- Start the Vaping container

## Monitoring Logs

To view the monitoring results:
```bash
./vaping_logs.sh
```

## Configuration

The default configuration is created in `~/.config/vaping/config.yaml`. You can modify this file to:
- Add/remove hosts to monitor
- Change monitoring intervals
- Adjust ping count
- Add new HTTP endpoints to check

The container will automatically use any changes you make to the configuration file after a restart.

## Container Management

- Stop the container: `docker stop vaping`
- Start the container: `docker start vaping`
- Restart the container: `docker restart vaping`
- Remove the container: `docker rm -f vaping`

## Troubleshooting

If you experience issues:

1. Check the logs using `./vaping_logs.sh`
2. Ensure the container has proper network access
3. Verify your configuration file syntax
4. Make sure fping is working within the container

## License

This project is open source and available under the MIT license.
