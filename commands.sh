# Install Necessary Package
pip3 install flask
pip3 install requests
pip3 install daylight
pip3 install temp
pip3 install cs50
pip3 install pandas

# For Linux
sudo yum update -y
sudo yum install git

# Point to the application file
export FLASK_ENV=development
export FLASK_APP=application.py

# Run the Dev server
flask run