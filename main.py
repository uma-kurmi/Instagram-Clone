from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.oauth2.id_token
from google.auth.transport import requests
from google.cloud import firestore, storage
from datetime import datetime
import starlette.status as status
import local_constants

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

firebase_request_adapter = requests.Request()
db = firestore.Client(project=local_constants.PROJECT_NAME)
client = storage.Client(project=local_constants.PROJECT_NAME)
bucket = client.bucket(local_constants.PROJECT_STORAGE_BUCKET)

def verify_firebase_token(request: Request):
    id_token = request.cookies.get("token")
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token, firebase_request_adapter)
            return claims
        except:
            return None
    return None

def upload_image_to_storage(file_content, filename, content_type):
    blob = bucket.blob(f"posts/{datetime.now().timestamp()}_{filename}")
    blob.upload_from_string(file_content, content_type=content_type)
    blob.make_public()
    return blob.public_url

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    user_token = verify_firebase_token(request)
    posts = []

    if user_token:
        user_id = user_token['user_id']
        user_doc = db.collection("User").document(user_id).get()

        if not user_doc.exists:
            username = user_token['email'].split("@")[0]
            db.collection("User").document(user_id).set({
                "username": username,
                "followers": [],
                "following": []
            })
            current_user = {
                "username": username,
                "followers": [],
                "following": []
            }
        else:
            current_user = user_doc.to_dict()

        usernames = current_user.get("following", [])
        usernames.append(current_user["username"])

        posts_query = db.collection("Post").where(filter=firestore.FieldFilter("Username", "in", usernames)).order_by("Date", direction=firestore.Query.DESCENDING).limit(50).stream()
        posts = []
        for doc in posts_query:
            post_data = doc.to_dict()
            post_data['id'] = doc.id
            
           
            comments_query = db.collection("Post").document(doc.id).collection("Comments").order_by("Date", direction=firestore.Query.DESCENDING).limit(5).stream()
            comments = [comment.to_dict() for comment in comments_query]
            post_data['comments'] = comments
            
           
            total_comments = len(list(db.collection("Post").document(doc.id).collection("Comments").stream()))
            post_data['has_more_comments'] = total_comments > 5
            
            posts.append(post_data)

    return templates.TemplateResponse("main.html", {"request": request, "user_token": user_token, "timeline": posts})

@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request):
    user_token = verify_firebase_token(request)
    if not user_token:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    user_id = user_token['user_id']
    user_ref = db.collection("User").document(user_id)
    user_doc = user_ref.get()

    if not user_doc.exists:
        username = user_token["email"].split("@")[0]
        user_ref.set({
            "username": username,
            "followers": [],
            "following": []
        })
        user_doc = user_ref.get()

    user_data = user_doc.to_dict()

    posts_query = db.collection("Post").where(filter=firestore.FieldFilter("Username", "==", user_data["username"])).order_by("Date", direction=firestore.Query.DESCENDING).stream()
    posts = []
    for doc in posts_query:
        post_data = doc.to_dict()
        post_data['id'] = doc.id
        
        
        comments_query = db.collection("Post").document(doc.id).collection("Comments").order_by("Date", direction=firestore.Query.DESCENDING).limit(5).stream()
        comments = [comment.to_dict() for comment in comments_query]
        post_data['comments'] = comments
        
       
        total_comments = len(list(db.collection("Post").document(doc.id).collection("Comments").stream()))
        post_data['has_more_comments'] = total_comments > 5
        
        posts.append(post_data)

    current_user = user_data
    is_following = False

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user_data": user_data,
        "posts": posts,
        "followers_count": len(user_data.get("followers", [])),
        "following_count": len(user_data.get("following", [])),
        "current_user": current_user,
        "is_following": is_following
    })

@app.post("/create_post")
async def create_post(request: Request):
    user_token = verify_firebase_token(request)
    if not user_token:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    form_data = await request.form()
    image = form_data.get("image")
    caption = form_data.get("caption")

    if not image or not caption:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    user_id = user_token['user_id']
    user_doc = db.collection("User").document(user_id).get()

    if not user_doc.exists:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    username = user_doc.to_dict()["username"]
    
    
    file_content = await image.read()
    filename = image.filename
    content_type = image.content_type

    image_url = upload_image_to_storage(file_content, filename, content_type)

    db.collection("Post").add({
        "Username": username,
        "ImageURL": image_url,
        "Caption": caption,
        "Date": datetime.now()
    })

    return RedirectResponse("/profile", status_code=status.HTTP_302_FOUND)

@app.get("/followers", response_class=HTMLResponse)
async def followers(request: Request):
    user_token = verify_firebase_token(request)
    if not user_token:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    user_id = user_token['user_id']
    user_doc = db.collection("User").document(user_id).get()
    followers = user_doc.to_dict().get("followers", [])

    return templates.TemplateResponse("followers.html", {
        "request": request,
        "followers": followers
    })

@app.get("/following", response_class=HTMLResponse)
async def following(request: Request):
    user_token = verify_firebase_token(request)
    if not user_token:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    user_id = user_token['user_id']
    user_doc = db.collection("User").document(user_id).get()
    following = user_doc.to_dict().get("following", [])

    return templates.TemplateResponse("following.html", {
        "request": request,
        "followings": following
    })

@app.get("/search", response_class=HTMLResponse)
async def search_get(request: Request):
    user_token = verify_firebase_token(request)
    if not user_token:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse("search.html", {"request": request})

@app.post("/search")
async def search_post(request: Request):
    user_token = verify_firebase_token(request)
    if not user_token:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    form_data = await request.form()
    search_query = form_data.get("search_query", "")

    users = db.collection("User").where(filter=firestore.FieldFilter("username", ">=", search_query)).where(filter=firestore.FieldFilter("username", "<=", search_query + "\uf8ff")).stream()
    results = [doc.to_dict()["username"] for doc in users]

    return templates.TemplateResponse("search.html", {"request": request, "search_results": results})

@app.get("/profile/{username}", response_class=HTMLResponse)
async def view_profile(request: Request, username: str):
    user_token = verify_firebase_token(request)
    if not user_token:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

  
    current_user_doc = db.collection("User").document(user_token['user_id']).get()
    current_user = current_user_doc.to_dict()

  
    users = db.collection("User").where(filter=firestore.FieldFilter("username", "==", username)).stream()
    target_user = None
    for user in users:
        target_user = user
        break

    if not target_user:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    user_data = target_user.to_dict()

   
    is_following = current_user["username"] in user_data.get("followers", [])

    posts_query = db.collection("Post").where(filter=firestore.FieldFilter("Username", "==", username)).order_by("Date", direction=firestore.Query.DESCENDING).stream()
    posts = []
    for doc in posts_query:
        post_data = doc.to_dict()
        post_data['id'] = doc.id
        
       
        comments_query = db.collection("Post").document(doc.id).collection("Comments").order_by("Date", direction=firestore.Query.DESCENDING).limit(5).stream()
        comments = [comment.to_dict() for comment in comments_query]
        post_data['comments'] = comments
        
       
        total_comments = len(list(db.collection("Post").document(doc.id).collection("Comments").stream()))
        post_data['has_more_comments'] = total_comments > 5
        
        posts.append(post_data)

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user_data": user_data,
        "posts": posts,
        "followers_count": len(user_data.get("followers", [])),
        "following_count": len(user_data.get("following", [])),
        "current_user": current_user,
        "is_following": is_following
    })

@app.post("/follow/{username}")
async def follow_user(request: Request, username: str):
    user_token = verify_firebase_token(request)
    if not user_token:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    user_id = user_token['user_id']
    user_ref = db.collection("User").document(user_id)

    current_data = user_ref.get().to_dict()

    target_users = db.collection("User").where(filter=firestore.FieldFilter("username", "==", username)).stream()
    target_doc = None
    for doc in target_users:
        target_doc = doc
        break

    if not target_doc:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    target_ref = db.collection("User").document(target_doc.id)

    user_ref.update({"following": firestore.ArrayUnion([username])})
    target_ref.update({"followers": firestore.ArrayUnion([current_data["username"]])})

    return RedirectResponse(f"/profile/{username}", status_code=status.HTTP_302_FOUND)

@app.post("/unfollow/{username}")
async def unfollow_user(request: Request, username: str):
    user_token = verify_firebase_token(request)
    if not user_token:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    user_id = user_token['user_id']
    user_ref = db.collection("User").document(user_id)

    current_data = user_ref.get().to_dict()

    target_users = db.collection("User").where(filter=firestore.FieldFilter("username", "==", username)).stream()
    target_doc = None
    for doc in target_users:
        target_doc = doc
        break

    if not target_doc:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    target_ref = db.collection("User").document(target_doc.id)

    user_ref.update({"following": firestore.ArrayRemove([username])})
    target_ref.update({"followers": firestore.ArrayRemove([current_data["username"]])})

    return RedirectResponse(f"/profile/{username}", status_code=status.HTTP_302_FOUND)

@app.get("/timeline", response_class=HTMLResponse)
async def timeline(request: Request):
    user_token = verify_firebase_token(request)
    if not user_token:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    user_id = user_token['user_id']
    current_user = db.collection("User").document(user_id).get().to_dict()

    usernames = current_user.get("following", [])
    usernames.append(current_user["username"])

    posts_query = db.collection("Post").where(filter=firestore.FieldFilter("Username", "in", usernames)).order_by("Date", direction=firestore.Query.DESCENDING).limit(50).stream()
    posts = []
    for doc in posts_query:
        post_data = doc.to_dict()
        post_data['id'] = doc.id
        
        
        comments_query = db.collection("Post").document(doc.id).collection("Comments").order_by("Date", direction=firestore.Query.DESCENDING).limit(5).stream()
        comments = [comment.to_dict() for comment in comments_query]
        post_data['comments'] = comments
        
        
        total_comments = len(list(db.collection("Post").document(doc.id).collection("Comments").stream()))
        post_data['has_more_comments'] = total_comments > 5
        
        posts.append(post_data)

    return templates.TemplateResponse("timeline.html", {"request": request, "timeline": posts})

@app.post("/comment/{post_id}")
async def add_comment(request: Request, post_id: str):
    user_token = verify_firebase_token(request)
    if not user_token:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    
    form_data = await request.form()
    comment_text = form_data.get("comment_text", "")
    
    if len(comment_text) > 200:
        comment_text = comment_text[:200] 

    comment_data = {
        "Username": user_token['email'].split('@')[0],
        "Comment": comment_text,
        "Date": datetime.now()
    }

    db.collection("Post").document(post_id).collection("Comments").add(comment_data)

    return RedirectResponse(f"/post/{post_id}", status_code=status.HTTP_302_FOUND)

@app.get("/post/{post_id}", response_class=HTMLResponse)
async def view_post(request: Request, post_id: str, show_all: bool = False):
    user_token = verify_firebase_token(request)
    if not user_token:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    post_doc = db.collection("Post").document(post_id).get()
    if not post_doc.exists:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

    post_data = post_doc.to_dict()

    
    comments_query = db.collection("Post").document(post_id).collection("Comments").order_by("Date", direction=firestore.Query.DESCENDING)
    
    if not show_all:
        comments_query = comments_query.limit(5) 
    
    comments = [comment.to_dict() for comment in comments_query.stream()]

    return templates.TemplateResponse("single_post.html", {
        "request": request,
        "post": post_data,
        "comments": comments,
        "post_id": post_id,
        "show_all": show_all  
    })

@app.get("/add_post", response_class=HTMLResponse)
async def add_post(request: Request):
    user_token = verify_firebase_token(request)
    if not user_token:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("add_post.html", {"request": request})