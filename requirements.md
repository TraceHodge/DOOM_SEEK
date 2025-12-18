For the server / raspberry pi setup, you can use the following commands to
install and configure the necessary software: Update the package list and
install the required packages:

* FastApi (for creating the server)
* Uvicorn (for running the server)
* OpenCV (for taking pictures and processing images)

*Look at docs folder for pictures of server packages*

Then for the Client, you will need to install the following packages:

* Pygame (for creating the controls)
* Numpy (for speed calculation)
* Requests (for making HTTP requests to the server)

*Look at docs folder for pictures of clients packages*

** Now for the static ip address **
Look At the static ip creation video in the readme to create a static ip for the raspberry pi after new the rounter is setup.
Once the static ip is created then go into the idex.html client code and change all the ip address for example http://192.168.8.104:8000/input
change the 192.168.8.104 to your newly created static ip address. 
