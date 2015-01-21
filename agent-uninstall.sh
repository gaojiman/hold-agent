#!/bin/bash
#
# Highwe Agent Installation Script
#
# @version		1.0.6
#

# Set environment
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

#save pwd
_p_w_d=$(pwd)

# Prepare output
echo -e "|\n|   Highwe Agent Uninstaller\n|   ===========================\n|"

# Root required
if [ $(id -u) != "0" ];
then
	echo -e "|   Error: You need to be root to uninstall the agent\n|"
	echo -e "|          The agent itself will NOT be running as root but instead under its own non-privileged user\n|"
	exit 1
fi

# Parameters required
if [ $# -lt 1 ]
then
    echo $#
	echo -e "|   Usage: bash $0 'token'\n|"
	exit 1
fi

#kill agent
pid=$(ps -ef | grep "agent.py $1" | grep -v grep | awk '{print $2}'|head -1)
if [ $pid ]
then
    kill $pid
fi

if [ -f /etc/agent/agent.py ]
then
	# Remove agent dir
	rm -Rf /etc/agent/agent.py
fi

if [ -f /etc/init.d/agent ]
then
	# Remove agent   server dir
	rm -Rf /etc/init.d/agent
fi

if [ -f $_p_w_d/agent.py ]
then
	# Remove agent   server dir
	rm -Rf $_p_w_d/agent.py
fi

#rm uninstall file
cd $_p_w_d
rm $0

echo -e "|\n|   Highwe Agent Uninstaller Success\n|   ===========================\n|"
