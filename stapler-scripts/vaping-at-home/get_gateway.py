#!/usr/bin/env python3
import subprocess
import sys
import platform

def get_gateway_ip():
    system = platform.system().lower()
    
    if system == "darwin":  # macOS
        try:
            # Try netstat first
            cmd = ["netstat", "-nr"]
            output = subprocess.check_output(cmd).decode()
            for line in output.split('\n'):
                if line.startswith('default'):
                    return line.split()[1]
        except:
            # Fallback to route
            try:
                cmd = ["route", "-n", "get", "default"]
                output = subprocess.check_output(cmd).decode()
                for line in output.split('\n'):
                    if 'gateway:' in line:
                        return line.split(':')[1].strip()
            except:
                pass
    
    elif system == "linux":
        try:
            # Try ip route
            cmd = ["ip", "route"]
            output = subprocess.check_output(cmd).decode()
            for line in output.split('\n'):
                if line.startswith('default'):
                    return line.split()[2]
        except:
            # Fallback to route
            try:
                cmd = ["route", "-n"]
                output = subprocess.check_output(cmd).decode()
                for line in output.split('\n'):
                    if line.startswith('0.0.0.0'):
                        return line.split()[1]
            except:
                pass

    return "192.168.1.1"  # Fallback default

if __name__ == "__main__":
    print(get_gateway_ip())
