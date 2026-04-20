const STORAGE_KEY = "vanilla-todo-items";

const form = document.getElementById("todo-form");
const input = document.getElementById("todo-input");
const list = document.getElementById("todo-list");
const emptyState = document.getElementById("empty-state");
const totalCount = document.getElementById("total-count");
const openCount = document.getElementById("open-count");
const doneCount = document.getElementById("done-count");

let todos = loadTodos();

function loadTodos() {
  const raw = localStorage.getItem(STORAGE_KEY);

  if (!raw) {
    return [];
  }

  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    console.error("Could not parse saved todos", error);
    return [];
  }
}

function saveTodos() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(todos));
}

function createTodo(text) {
  return {
    id: crypto.randomUUID(),
    text,
    done: false,
  };
}

function addTodo(text) {
  todos.unshift(createTodo(text.trim()));
  saveTodos();
  render();
}

function toggleTodo(id) {
  todos = todos.map((todo) => {
    if (todo.id !== id) {
      return todo;
    }

    return {
      ...todo,
      done: !todo.done,
    };
  });

  saveTodos();
  render();
}

function deleteTodo(id) {
  todos = todos.filter((todo) => todo.id !== id);
  saveTodos();
  render();
}

function updateStats() {
  const done = todos.filter((todo) => todo.done).length;
  const open = todos.length - done;

  totalCount.textContent = String(todos.length);
  openCount.textContent = String(open);
  doneCount.textContent = String(done);
}

function render() {
  list.innerHTML = "";
  updateStats();

  if (todos.length === 0) {
    emptyState.hidden = false;
    return;
  }

  emptyState.hidden = true;

  todos.forEach((todo) => {
    const item = document.createElement("li");
    item.className = todo.done ? "todo-item done" : "todo-item";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = todo.done;
    checkbox.addEventListener("change", () => toggleTodo(todo.id));

    const text = document.createElement("span");
    text.className = "todo-text";
    text.textContent = todo.text;

    const deleteButton = document.createElement("button");
    deleteButton.className = "delete-btn";
    deleteButton.type = "button";
    deleteButton.textContent = "Delete";
    deleteButton.addEventListener("click", () => deleteTodo(todo.id));

    item.append(checkbox, text, deleteButton);
    list.appendChild(item);
  });
}

form.addEventListener("submit", (event) => {
  event.preventDefault();

  const text = input.value.trim();
  if (!text) {
    return;
  }

  addTodo(text);
  input.value = "";
  input.focus();
});

render();
