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
echo -e "|\n|   Highwe Agent Installer\n|   ===========================\n|"

# Root required
if [ $(id -u) != "0" ];
then
	echo -e "|   Error: You need to be root to install the agent\n|"
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


# Attempt to delete previous agent
if [ -f /etc/agent/agent.py ]
then
	# Remove agent dir
	rm -Rf /etc/agent/agent.py
fi

# Create agent dir
mkdir -p /etc/agent

# Download agent
echo -e "|   Downloading agent to /etc/agent \n|\n|   + $(wget -nv -o /dev/stdout -O /etc/agent/agent.py --no-check-certificate  http://highwe.net/static/agent.py)"

if [ -f /etc/agent/agent.py ]
then
	# Modify user permissions
	chmod -R a+rx /etc/agent
	
    #start agent
    cd /etc/agent
    pid=$(ps -ef | grep "agent.py $1" | grep -v grep | awk '{print $2}'|head -1)
    if [ $pid ]
    then
        kill $pid
    fi
	# Attempt to delete installation script
	if [ -f $0 ]
	then
		rm -f $0
	fi
else
	# Show error
	echo -e "|\n|   Error: The agent can not be created\n|"
fi

pid=$(ps -ef | grep "agent.py $1" | grep -v grep | awk '{print $2}'|head -1)
if [ $pid ]
then
    kill $pid
fi

# Check if chkconfig is installed
if [ ! -n "$(command -v chkconfig)" ] 
then
	if [ -n "$(command -v apt-get)" ]
	then
		echo -e "|\n|   Notice: Installing required package 'chkconfig' via 'apt-get'"
	    apt-get -y update
	    apt-get -y install chkconfig
	elif [ -n "$(command -v yum)" ]
	then
		echo -e "|\n|   Notice: Installing required package 'chkconfig' via 'yum'"
	    yum -y install chkconfig
	elif [ -n "$(command -v pacman)" ]
	then
		echo -e "|\n|   Notice: Installing required package 'chkconfig' via 'pacman'"
	    pacman -S --noconfirm chkconfig
    fi
fi


if [ ! -n "$(command -v chkconfig)" ] && [ ! -n "$(command -v sysv-rc-conf)" ]
then
	if [ -n "$(command -v apt-get)" ]
	then
		echo -e "|\n|   Notice: Installing required package 'sysv-rc-conf' via 'apt-get'"
	    apt-get -y update
	    apt-get -y install sysv-rc-conf
	elif [ -n "$(command -v yum)" ]
	then
		echo -e "|\n|   Notice: Installing required package 'sysv-rc-conf' via 'yum'"
	    yum -y install sysv-rc-conf
	elif [ -n "$(command -v pacman)" ]
	then
		echo -e "|\n|   Notice: Installing required package 'sysv-rc-conf' via 'pacman'"
	    pacman -S --noconfirm sysv-rc-conf
    fi
fi


if [ ! -n "$(command -v chkconfig)" ] && [ ! -n "$(command -v sysv-rc-conf)" ]
then
    # Show error
    echo -e "|\n|   Error: agent  is could not be conf server because chkconfig or sysv-rc-conf is could not be installed\n|"
    exit 1
fi	

if [ ! -d /etc/init.d ]
then
	# create /etc/init.d dir
    mkdir /etc/init.d
fi

    # Download agent
echo -e "|   Downloading agent to /etc/init.d \n|\n|   + $(wget -nv -o /dev/stdout -O /etc/init.d/agent --no-check-certificate  http://highwe.net/static/agent)"
    chmod a+x /etc/init.d/agent

    #sed USERKEY  $1
    sed -i "s/userkey/$1/g" /etc/init.d/agent

    if [ -n "$(command -v chkconfig)" ]
    then
    	chkconfig agent on
    	service agent start
    elif [ -n "$(command -v sysv-rc-conf)" ]
    then
    	echo -e "|\n|   Notice: Starting 'agent' via 'service'"
        sysv-rc-conf agent on
    	service agent start

    elif [ -n "$(command -v pacman)" ]
    then
    	echo -e "|\n|   Notice: Starting 'agent' via 'systemctl'"
        systemctl start  agent
        systemctl enable agent
    fi

#rm install file
cd $_p_w_d
rm $0
