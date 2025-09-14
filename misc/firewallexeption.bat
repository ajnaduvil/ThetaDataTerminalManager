@echo off
echo Adding firewall rules for Theta Terminal...
PowerShell -Command "New-NetFirewallRule -DisplayName 'Theta Terminal - HTTP Out' -Direction Outbound -Protocol TCP -LocalPort 25510 -Action Allow"
PowerShell -Command "New-NetFirewallRule -DisplayName 'Theta Terminal - WebSocket Out' -Direction Outbound -Protocol TCP -LocalPort 25520 -Action Allow"
PowerShell -Command "New-NetFirewallRule -DisplayName 'Theta Terminal - Client Out' -Direction Outbound -Protocol TCP -LocalPort 11000 -Action Allow"
PowerShell -Command "New-NetFirewallRule -DisplayName 'Theta Terminal - Stream Out' -Direction Outbound -Protocol TCP -LocalPort 10000 -Action Allow"
PowerShell -Command "New-NetFirewallRule -DisplayName 'Theta Terminal - HTTP In' -Direction Inbound -Protocol TCP -LocalPort 25510 -Action Allow"
PowerShell -Command "New-NetFirewallRule -DisplayName 'Theta Terminal - WebSocket In' -Direction Inbound -Protocol TCP -LocalPort 25520 -Action Allow"
PowerShell -Command "New-NetFirewallRule -DisplayName 'Theta Terminal - Client In' -Direction Inbound -Protocol TCP -LocalPort 11000 -Action Allow"
PowerShell -Command "New-NetFirewallRule -DisplayName 'Theta Terminal - Stream In' -Direction Inbound -Protocol TCP -LocalPort 10000 -Action Allow"
echo Done.
pause