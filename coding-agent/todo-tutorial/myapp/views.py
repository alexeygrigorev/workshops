from django.shortcuts import render, redirect
from .models import Todo
from .forms import TodoForm


def todo_list(request):
    todos = Todo.objects.all()
    if request.method == 'POST':
        if 'complete' in request.POST:
            todo_id = request.POST['complete']
            todo = Todo.objects.get(id=todo_id)
            todo.completed = not todo.completed
            todo.save()
            return redirect('todo_list')
        else:
            form = TodoForm(request.POST)
            if form.is_valid():
                form.save()
                return redirect('todo_list')
    else:
        form = TodoForm()
    return render(request, 'todo_list.html', {'todos': todos, 'form': form})


def delete_todo(request, todo_id):
    todo = Todo.objects.get(id=todo_id)
    todo.delete()
    return redirect('todo_list')