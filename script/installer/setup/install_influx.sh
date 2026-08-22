
sudo systemctl status --no-pager influxdb
retVal=$?
if  [ $retVal -eq 0 ];then
    echo "InfluxDB already installed, skipping install"
    exit 0
fi

# influxdata-archive_compat.key GPG fingerprint:
# Ubuntu and Debian
# Add the InfluxData key to verify downloads and add the repository
curl --silent --location -O https://repos.influxdata.com/influxdata-archive.key
gpg --show-keys --with-fingerprint --with-colons ./influxdata-archive.key 2>&1 \
| grep -q '^fpr:\+24C975CBA61A024EE1B631787C3D57159FC2F927:$' \
&& cat influxdata-archive.key \
| gpg --dearmor \
| sudo tee /etc/apt/keyrings/influxdata-archive.gpg > /dev/null \
&& echo 'deb [signed-by=/etc/apt/keyrings/influxdata-archive.gpg] https://repos.influxdata.com/debian stable main' \
| sudo tee /etc/apt/sources.list.d/influxdata.list
# Install influxdb
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update && sudo apt-get install influxdb2 -y

