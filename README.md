# Deploying Serverless AI Models on AWS Lambda

AWS Lambda is a serverless compute service which allows us to execute code in response to triggers like other AWS services or external sources like web or mobile applications. We can use AWS Lambda to Deploy our AI Models by integrating EFS with Lambda to overcome the storage restrictions of Lambda. Deploying AI models on a serverless platform like AWS Lambda reduces our costs significantly as the billing is based only on the number of invocations and compute time which can be covered in the free-tier for the most part.

This repository is a part of [my workshop at CellStrat](https://www.meetup.com/Disrupt-4-0/events/275681532).

---

## Update [14 July 2021]

An alternate method for uploading models and libraries to EFS is by uploading them to S3 and then triggering a lambda function which downloads the files from S3 to EFS directly without using EC2 at all. The VPC, EFS, Lambda and S3 resources can be created automatically using this [CloudFormation template](cloudformation-templates/vpc-efs-lambda.yaml). The actual model lambda function creation still has to be manual though as your code could vary depending on your model.

## Update [13 July 2021]

The VPC, EFS and EC2 resources can be created automatically using this [CloudFormation template](cloudformation-templates/vpc-efs-ec2.yaml). The lambda function creation still has to be manual though as your code could vary depending on your model.

---

## Lambda AI Deployment - Cheat Sheet (from Scratch)

This is a cheat sheet of the steps followed in the workshop for the attendees to use as a reference in the future.

#### 1. VPC, Security Group and IAM Role
_Skip this step if you wish to use the default VPC but you have to make sure these configurations are present in your default VPC_.

Go to VPC in your AWS Console:

1. Create a VPC with an IPv4 CIDR Block of your choice. Example: `10.0.0.0/16`
    1. Enable DNS Hostnames in your VPC.
3. Create 3 Subnets inside the VPC with your choice of availability zones and CIDR blocks. Example CIDR blocks you can choose: `10.0.0.0/21`, `10.0.32.0/21`, `10.0.64.0/21`
4. Create an Internet Gateway and attach it to your VPC that you have created.
5. Create a Route Table in your VPC.
    1. Associate the subnets you had created earlier in this route table.
    2. Edit the routes and add the internet gateway you just created with destination  `0.0.0.0/0` and target as your internet gateway.
6. Create a security group
    1. Give it a name and description
    2. Select your VPC
    3. Add an inbound rule with Type `Custom TCP`, Port Range `2049` and Source `Anywhere`
    4. Leave the outbound rules at the default but make sure it has Type `All Traffic` and Destination as `0.0.0.0/0`

7. Go to IAM in your AWS Console and create a new role with lambda use case
    1. Attach the following policies in the permissions tab:
        - `AWSLambdaExecute`
        - `AWSLambdaVPCAccessExecutionRole`
        - `AmazonElasticFileSystemClientFullAccess`
    2. Give your role a name and create it.


#### 2. EFS
Go to EFS in your console:
1. Create a new file system, name it and select your VPC in the dropdown. Click on Customize
2. Go to Network Access section and select the subnets in the Mount Targets that you had created earlier which would probably be selected by default.
3. However, remove the default security group in the Mount Targets and select the Security Group you had created earlier.
4. Then just leave the other sections with the default settings and continue clicking next and then create. After your EFS is created make note of the ID which should look something like this `fs-xxxxxx`.
5. After your EFS is created, click on it and create a new `Access Point` with the following configurations:
    - Name: your choice
    - Root directory path: your choice and this will be used later a lot. Example: `/ml`
    - POSIX User
        - User ID: `1000`
        - Group ID: `1000`
    - Root directory creation permissions
        - Owner User ID: `1000`
        - Owner Group ID: `1000`
        - POSIX permission on root directory: `777`

#### 4. Lambda - Part 1

Configuring Lambda with VPC and EFS:
1. Create a lambda function.
2. Name it and select Python 3.7 as the runtime.
3. Change the default execution role and select the IAM role you had created earlier.
4. Click on Advanced Settings and select your VPC.
5. Select all the subnets you had created and select the security group created earlier.
6. Click on Create and wait for the function to get created.
7. After the function is created, Click on Add File System.
8. Select your EFS from the down and also select the access point you created.
9. Type the mount path as `/mnt/<your root dir path>`. Example: `/mnt/ml`. Now click on Save.

Testing the EFS Integration:
1. Go to the lambda code editor and paste the following code in the `lambda_function.py`:

```python
import json
import os

def lambda_handler(event, context):

    print('Before:', os.listdir('/mnt/ml'))

    with open('/mnt/ml/hello.txt', 'w') as f:
        f.write('Hello EFS from Lambda')

    print('After:', os.listdir('/mnt/ml'))

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
```
2. Create a test event and name is dummy for now.
3. Click on Test and make sure there are no errors. Your Execution Function Logs should look something like this:
```
START RequestId: 3aad2609-0d18-4406-9b5a-1756af3b9fc4 Version: $LATEST
Before: []
After: ['hello.txt']
END RequestId: 3000609-0000-4006-900a-1000af3b9fc4
REPORT RequestId: 3000609-0000-4006-900a-1000af3b9fc4	Duration: 30.77 ms	Billed Duration: 31 ms	Memory Size: 128 MB	Max Memory Used: 49 MB	Init Duration: 121.57 ms
```
4. This indicates that the EFS integration was successful as were able to write a file in our EFS.

#### 5. Installing Packages in EFS via EC2
To install libraries and upload our model files to EFS we need to create and use an EC2 instance:
1. Go to EC2 in your console, go to instances and launch an EC2 instance.
2. Choose Ubuntu 20.04 as the Amazon Machine Image (AMI)
3. Select t2.medium as the instance type
4. Under Configure Instance:
    1. Select your VPC in Network
    2. Select any subnet and make note of the availability zone of the subnet you are choosing
    3. Enable Auto-Assign Public IP
    4. Leave the remaining stuff in default and click Next.
5. Change storage to atleast 12 GB and click Next.
6. Add an optional Name tag with the name that you want to give to your instance.
7. In the security group section, choose "Create a new security group" and give it a name and description.
8. Add a Custom TCP Rule with Port `2049` and Source `Anywhere`
9. Click on Review and Launch.
10. Now click on Launch. This will bring a pop up for creating an SSH key pair.
    1. Choose create a new key pair
    2. Give your key a name and hit the download button
    3. Keep this `.pem` file very safe as it is will be used to gain access into the instance.
11. Wait for the newly created EC2 instance to change to Running State.

Connecting to EC2 and Mounting EFS:
1. In your local system, go to the `.pem` file you just downloaded and take full ownership of the file and make sure it is private to you. On mac and linux you can use the following command in terminal `chmod 400 "<path to your pem file>"`. On windows refer [this](https://superuser.com/questions/1296024/windows-ssh-permissions-for-private-key-are-too-open)
2. Right click on your instance and click on connect. Go to SSH client tab and copy the exmample command which should look something like this: `ssh -i "<your pem file path>" ubuntu@ec2-XX-XX-XXX-XXX.compute-1.amazonaws.com`
3. Open a terminal / command prompt in the location of your pem file and run this command to connect to your instance via SSH.
4. Now run these commands:
```
sudo apt-get update
sudo apt-get install nfs-common -y
sudo mkdir efs-mount
```
5. Now we mount the EFS by running this command `sudo mount -t nfs4 fs-xxxxxx.efs.us-east-1.amazonaws.com:/ efs-mount` replace `fs-xxxxxx` with your EFS ID.
6. Now we can cd into EFS by typing `cd efs-mount/ml`

We will first install python3.7 on our instance and change the priority. Run the following commands:

```
sudo apt update
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.7 -y
sudo apt-get install python3-pip -y

sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 2
sudo update-alternatives --config python3 # In the last command choose the option which has python3.7
```

Installing the libraries on EFS:
1. Make a `lib` folder to install all the libraries.
2. `cd` into the `lib` folder.
3. Now you can install your libraries by running `pip3 install <your package name> -t ./`
4. You can also create a `models` folder in `efs-mount/ml/` and upload your model files via `scp`. To copy files from your local system to your EC2 instance, open a new terminal and use the following command: `scp -i "<path to your pem file>" '<path to model file>' ubuntu@ec2-XX-XXX-XXX-XXX.compute-1.amazonaws.com:efs-mount/ml/models/`


#### 6. Lambda - Part 2
Uploading/Writing our main inference code for the model.
1. Upload your inference code as a zip file or write your code in the lambda code editor.
2. Add the Python Environment Variable so Lambda knows where to look for the libraries installed in EFS: `PYTHONPATH = /mnt/ml/lib`. You can add additional environment variables for things like model files path, example: `MODEL_DIR = /mnt/ml/models`.
3. Edit the Basic Settings and Assign RAM as per your model and change timeout to atleast a minute but it depends on your model.
4. Configure test events for your lambda function and test it.

#### 7. API Gateway
Create an HTTP API and test with python on your local system
1. Go to API Gateway and create an HTTP API
2. Create a POST route
3. Add Lambda integration for that route
4. Configure CORS and set it to `Access-Control-Allow-Origin: *, Access-Control-Allow-Headers: *, Access-Control-Allow-Methods: POST`
5. Copy the API URL and now you can test your model by calling the API from wherever you want like a web app or another flask server etc.


#### 8. Deploying a Second Model
After this, if you wish to deploy a second model, you need not go through the entire process again. You just have to follow a subset of steps i.e.:
1. Connect to EC2
2. Mount the EFS by running this command `sudo mount -t nfs4 fs-xxxxxx.efs.us-east-1.amazonaws.com:/ efs-mount` replace `fs-xxxxxx` with your EFS ID.
3. Install additional libraries in `efs-mount/ml/lib` with `pip3 install <package> -t ./`.
4. If you want to upload model files then upload them to `efs-mount/ml/model` via SCP or anyother method of your choice.
5. Create a new lambda function and make the appropriate configurations (VPC, EFS, Memory and Timeout, Environment Variables) and upload/write your code.
6. Create a new POST route in your API in API Gateway with your new lambda integrated.


**Note:** Make sure to stop your EC2 instance after you use it as it will incur costs.

## Support

If you need any help in deploying your models on AWS Lambda or are facing any errors/issues, feel free to Create an Issue in this repository.
