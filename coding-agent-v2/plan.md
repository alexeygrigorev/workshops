# Todo App Plan

Build a browser-based todo app inside the Django project template.

The Django project is only the shell for serving the page. The todo functionality itself should be implemented on the frontend with plain HTML and vanilla JavaScript.

## Technical constraints

- use plain HTML
- use vanilla JavaScript
- use `localStorage` for persistence
- do not use frontend frameworks
- do not use the Django database for storing todos
- keep the todo state in the browser

## Project shape

Use the existing Django project structure.

The result should be a Django page that renders a todo app in the browser. The page can be served from an existing template or from a new template added to the project.

## Functional requirements

The app should allow the user to:

- add a new todo item
- mark a todo item as completed
- unmark a completed todo item
- delete a todo item
- keep todos after page reload by saving them in `localStorage`

## UI requirements

The page should contain:

- a title
- a short subtitle or helper text
- an input for entering a new todo
- a button for adding the todo
- a list of todos
- a visible empty state when there are no todos

Each todo item should show:

- a checkbox or toggle for completion
- the todo text
- a delete action

Completed todos should look visibly different from active todos.

## Styling

Use the styling that already exists in the Django template.

If TailwindCSS or Font Awesome are already available in the project, reuse them. Do not introduce a new frontend stack.

## Data format

Store the todos in `localStorage` as JSON.

Each todo item should have at least:

- an id
- a text field
- a completed flag

## Implementation guidance

- keep the logic simple
- prefer one template and one JavaScript file
- load the saved todos when the page opens
- re-render the list after each change
- save to `localStorage` after add, toggle, and delete actions
