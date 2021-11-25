from os import stat
from typing import Optional, List
from fastapi import FastAPI, Response, status, HTTPException
from fastapi.params import Body, Depends
from pydantic import BaseModel
from random import randrange
import psycopg2
from psycopg2.extras import RealDictCursor
import time

from sqlalchemy.orm import session
#Using SQLAlchemy
from . import models, schemas
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Anytime you have something that might fail a connection, you should use a try catch block
while True:
    try:
        #for now we will hardcode it
        conn =  psycopg2.connect(host = 'localhost', database = 'fastapi', 
                                user = 'postgres', password = 'password123',
                                cursor_factory = RealDictCursor)
        # This is what we will use to execute sql statements
        cursor = conn.cursor()
        print ("Database connection was successful")
        break
    except Exception as error:
        print ("Connection to database has failed")
        print ("Error:", error)
        time.sleep(2)

# Create a variable to save a couple posts for testing.
my_posts = [{"title" : "title of post 1", "content" : "content of post 1", "id" : 1}, 
{"title" : "favourite foods", "content" : "I like pizza", "id" : 2}]

def find_post(id):
    for p in my_posts:
        if p["id"] == id:
            return p

def find_index_post(id):
    for i, p in enumerate(my_posts):
        if p['id'] == id:
            return i

# Path Operation (route) - @app is the decorator, get is the method, ("/") is the path and root is the function
@app.get("/") # decorator - turns this function into a get path operation
def root():
    return { "message" : "Hello World" }

@app.get("/posts", response_model=List[schemas.Post])
def get_posts(db: session = Depends(get_db)):
    # raw SQL
    # cursor.execute("""SELECT * FROM posts""")
    # posts = cursor.fetchall()
    posts = db.query(models.Post).all()
    return posts

# title string, content string
# @app.post("/createposts")
# extract all of the fields from the body, convert to python dictionary and store inside variable payLoad
# def create_posts(payLoad: dict = Body(...)):
#     print(payLoad)
#     return { "new_post" : f"title: {payLoad['title']} content: {payLoad['content']}"}

# calling the class Post in the function allows us to validate for a title and content from the user
# @app.post("/posts", status_code=status.HTTP_201_CREATED) # set the status code to 201 when creating
# def create_posts(post: Post):
    # print(post)
    # This will take the pydantic model and convert it to a dictionary
    # print(post.dict())
    # post_dict = post.dict()
    # post_dict["id"] = randrange(0, 100000)
    # my_posts.append(post_dict)
    #%s is essentially a variable for title content and published, it sanitizes and protects against sql injection.
    # cursor.execute("""INSERT INTO posts (title, content, published) VALUES (%s, %s, %s) RETURNING * """, 
    #                 (post.title, post.content, post.published))
    # new_post = cursor.fetchone()
    # # Save the data
    # conn.commit()
    # return { "data" : new_post }

@app.post("/posts", status_code=status.HTTP_201_CREATED, response_model=schemas.Post)
def create_posts(post: schemas.PostCreate, db: session = Depends(get_db)):
    # Create a brand new post
    # new_post = models.Post(title=post.title, content=post.content, published=post.published)
    new_post = models.Post(**post.dict())
    # Add it to our database
    db.add(new_post)
    # Commit the changes
    db.commit()
    # Retrieve the new_post we created and store it back into the variable new_post
    db.refresh(new_post)
    return new_post
    

# {id} is a path parameter
@app.get("/posts/{id}", response_model=schemas.Post)
# if we make id an int here we don't have to convert it in the body, and it validates that the id is a valid integer
def get_post(id: int, db: session = Depends(get_db)):
    # print(id)
    # return {"post_detail" : f"Here is post {id}"}
    # Have to convert id to an int because it's default is str
    # post = find_post(int(id))
    # cursor.execute("""SELECT * FROM posts WHERE id = %s """, (str(id)))
    # post = cursor.fetchone()
    post = db.query(models.Post).filter(models.Post.id == id).first()
    if not post:
        # This is a cleaner way to deal with a post that doesn't have the id a user input
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail=f"post with id: {id} was not found")
        # response.status_code = status.HTTP_404_NOT_FOUND
        # return {"message" : f"post with id: {id} was not found"}
    return post

@app.delete("/posts/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(id: int, db: session = Depends(get_db)):
    # find the index in the array that has required id
    # my_posts.pop(index)
    # cursor.execute("""DELETE FROM posts WHERE id = %s RETURNING *""", (str(id),))
    # deleted_post = cursor.fetchone()
    # conn.commit()
    # index = find_index_post(id)
    post = db.query(models.Post).filter(models.Post.id == id)
    if post.first() == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post with id: {id} does not exist")
    post.delete(synchronize_session=False)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.put("/posts/{id}", response_model=schemas.Post)
def update_post(id: int, updated_post: schemas.PostCreate, db: session = Depends(get_db)):
    # cursor.execute("""UPDATE posts SET title = %s, content = %s, published = %s WHERE id = %s RETURNING *""", 
    #                 (post.title, post.content, post.published, str(id)))
    # updated_post = cursor.fetchone()
    # conn.commit()
    # index = find_index_post(id)
    # A query to find a post with the specific ID
    post_query = db.query(models.Post).filter(models.Post.id == id)
    # Then we grab that specific post with .first()
    post = post_query.first()
    # If it doesn't exist, we will send back a 404
    if post == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post with id: {id} does not exist")
    # If it does exist we update that post with the selected fields "post.dict()"
    post_query.update(updated_post.dict(), synchronize_session=False)
    # Then we save it or commit it to the database
    db.commit()
    # post_dict = post.dict()
    # post_dict['id'] = id
    # Once we convert to dictionary and get the id of the post we want to update, we get the post with the index and replace with post_dict.
    # That is how we update that specific spot in the array.
    # my_posts[index] = post_dict
    return post_query.first()

