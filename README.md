# Instagram Clone
A simple Instagram-style social media web application built using FastAPI, Firebase Authentication, Firestore, and Google Cloud Storage.
The application allows users to log in using Google, create posts with images, follow other users, and view a timeline of posts — similar to core Instagram functionality.

# Features
The application supports the following functionality:

User authentication with Firebase Google Login

Upload posts with images

View a global timeline of posts

View individual user profiles

Follow and unfollow users

View followers and following lists

Search for other users.

Image storage using Google Cloud Storage

# Tech Stack

Backend:

Python

FastAPI

Frontend:

HTML

Jinja2 Templates

CSS

JavaScript

Database & Cloud:

Firebase Authentication

Google Firestore

Google Cloud Storage

# Project Structure

Instagram-Clone
│
├── main.py                 # FastAPI application entry point
├── local_constants.py      # Firebase configuration and project constants
├── requirements.txt        # Python dependencies
│
├── static/                 # Static frontend assets
│   ├── styles.css          # Application styling
│   └── firebase-login.js   # Firebase authentication logic
│
├── templates/              # Jinja2 HTML templates for UI rendering
│   ├── main.html           # Main landing page
│   ├── timeline.html       # User timeline / feed
│   ├── profile.html        # User profile page
│   ├── search.html         # User search page
│   ├── add_post.html       # Create new post page
│   ├── followers.html      # Followers list
│   ├── following.html      # Following list
│   └── single_post.html    # Individual post view

# How the Application Works
A user logs in using Firebase Google Authentication.
After authentication, a secure token is stored in cookies.
The backend verifies the token using Firebase.
User data and posts are stored in Google Firestore.
Uploaded images are stored in Google Cloud Storage.
Posts are retrieved and displayed on the user's timeline.
