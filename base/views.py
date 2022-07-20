from email import message
import email
from http.client import HTTPResponse
from unicodedata import name
from django.http import HttpResponseRedirect
from multiprocessing import context
from django.db.models import Q
import re
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout 
from .models import Room, Topic, Message
from .forms import RoomForm, UserForm



def loginPage(request):

    page = 'login'

    #preventing logged in user from re-logging while logged in
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            user = User.objects.get(username=username)
        except:
            #rem to output the essage on main.htm
            messages.error(request, 'This user does not exist!')

        #authenticate user -- check if username and password belong
        user = authenticate(username=username, password=password)

        if user is not None:
            #adding session id in the db and browser 
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'The username or password is incorrect!')


    context = {'page':page}
    return render(request, 'base/login_register.htm', context)


def registerPage(request):
    form = UserCreationForm()
    
    if request.method == "POST":

        #binding data from fields to the form
        form = UserCreationForm(request.POST)

        #checking validity of the data 
        if form.is_valid():
        #saving bt not committing so that we clean data in tis case username to lowercase
            user = form.save(commit=False)
            user.username = user.username.lower()
            user.save()
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'An error occured during regestration, please try again')

    context = {'form':form}
    return render(request, 'base/login_register.htm', context)


def logoutUser(request):
    logout(request)
    return redirect('home')



def home(request):
    #querying the database 
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    # 'topic__name = q' implies querying pwards to the parent
    # 'topic__name__icontains' -- 'i' removes case sensitivt 
    rooms = Room.objects.filter(
        Q(topic__name__icontains = q) |
        Q(name__icontains = q)|
        Q(description__icontains = q)
        )
    topics = Topic.objects.all()[0:5]
    # .count is faster than .len
    room_count = rooms.count
    room_messages = Message.objects.filter(Q(room__topic__name__icontains=q))
    

    context = {"rooms":rooms, "topics":topics, "room_count":room_count, 
                "room_messages":room_messages}

    return render(request, 'base/home.htm', context)




def room(request,pk):
    room = Room.objects.get(id=pk)
    #gettig all messages belong to a specific room. room.message_set.all() => room is the specific room
    #message is the child class were are querying
    room_messages = room.message_set.all().order_by('-created')
    participants = room.participants.all()

    if request.method == 'POST':
        messages = Message.objects.create(
            user= request.user,
            room=room,
            body=request.POST.get('comment')
        )
        room.participants.add(request.user)
        #redirect to have it back to a 'get' request
        return redirect('room', pk=room.id)


    context = {"room":room, "room_messages":room_messages, 
                "participants":participants} 
    return render(request, 'base/room.htm', context)


def userProfile(request, pk):
    user = User.objects.get(id=pk)
    # childclass_set to query a childclass for its objects
    rooms = user.room_set.all()
    room_messages = user.message_set.all()
    topics = Topic.objects.all()
    context = {"user":user, "rooms":rooms, "room_messages":room_messages,
                "topics":topics}
    return render(request, 'base/profile.html', context)



#decorator to allow only logined in users to create a room
@login_required(login_url='/login')

def createRoom(request):
    form = RoomForm()
    topics = Topic.objects.all()
    #processing the data
    if request.method == 'POST':
        topic_name = request.POST.get('topic')
        topic, created = Topic.objects.get_or_create(name=topic_name)

        Room.objects.create(
            host = request.user,
            topic = topic,
            name = request.POST.get('name'),
            description = request.POST.get('description'),
        )

        # form = RoomForm(request.POST)
        # if form.is_valid:
        #     room = form.save(commit=False)
        #     room.host=request.user
        #     room.save()
            #redirecting user to home after submitting form
        return redirect('home')

    context = {"form":form, "topics":topics} 
    return render(request,'base/room_form.html', context)




@login_required(login_url='/login')

def updateRoom(request,pk):
    room = Room.objects.get(id=pk)
    #passing 'instance=room'parameters to prefill form fields with data otherwise it will be blank
    form = RoomForm(instance=room)
    topics = Topic.objects.all()

    #restricting any user from updatig a room unless its the room creator(not working)
    if request.user != room.host:
       #return HTTPResponse('You are not allowed!!')
        return HttpResponseRedirect('You are not allowed!!')

    if request.method == 'POST':
        #prefill the form 
        topic_name = request.POST.get('topic')
        topic, created = Topic.objects.get_or_create(name=topic_name)
        room.name = request.POST.get('name')
        room.topic = topic
        room.description = request.POST.get('description')
        room.save()

        return redirect('home')
    context = {'form':form, "topics":topics, "room":room}
    return render(request,'base/room_form.html', context)





@login_required(login_url='/login')   
    
def deleteRoom(request,pk):
    room = Room.objects.get(id=pk)

    if request.user != room.host:
        return HTTPResponse('You are not allowed!!')

    if request.method == 'POST':
        room.delete()
        return redirect('home')
    #context is {'obj':room}, in delete.htm we are accessing room/message as 'obj'
    return render(request,'base/delete.htm', {'obj':room})


    #deleting room comment/message functionality
@login_required(login_url='/login')   
    
def deleteMessage(request, pk):
    message = Message.objects.get(id=pk)

    # if request.user != message.user:
    #     return HTTPResponse('You are not allowed!!')

    if request.method == 'POST':
        message.delete()
        return redirect('home')
    #context is {'obj':room}, in delete.htm we are accessing room/message as 'obj'
    return render(request,'base/delete.htm', {'obj':message})



#updating user details functionality
@login_required(login_url='login')

def updateUser(request):
    user = request.user
    form = UserForm(instance=user)

    #process the form input(data)
    if request.method == 'POST':
        form= UserForm(request.POST, instance= user)
        if form.is_valid():
            form.save()
            return redirect('user-profile', pk=user.id)

    return render(request, 'base/update-user.html', {'form':form})



def topicsPage(request):

    q = request.GET.get('q') if request.GET.get('q') != None else ''

    topics = Topic.objects.filter(name__icontains=q)
    rooms = Room.objects.all()
    context = {"topics":topics, "rooms":rooms}
    return render(request, 'base/topics.html', context)


def activityPage(request):
    room_messages = Message.objects.all()

    context = {"room_messages":room_messages}
    return render(request, 'base/activity.html', context)