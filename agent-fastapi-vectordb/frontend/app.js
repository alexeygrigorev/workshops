const $messages = document.getElementById("messages");
const $form = document.getElementById("ask-form");
const $question = document.getElementById("question");
const $submit = document.getElementById("submit");
const $course = document.getElementById("course");


async function loadCourses() {
    const response = await fetch("/api/courses");
    const data = await response.json();
    for (const c of data.courses) {
        const option = document.createElement("option");
        option.value = c.id;
        option.textContent = c.name;
        $course.appendChild(option);
    }
}


function addUserMessage(text) {
    const el = document.createElement("div");
    el.className = "msg user";
    el.textContent = text;
    $messages.appendChild(el);
    el.scrollIntoView({ behavior: "smooth" });
}


function addAssistantMessage() {
    const wrap = document.createElement("div");
    wrap.className = "msg assistant";

    const answer = document.createElement("div");
    answer.className = "answer";
    wrap.appendChild(answer);

    const trace = document.createElement("details");
    trace.className = "trace";
    const summary = document.createElement("summary");
    summary.textContent = "agent trace";
    trace.appendChild(summary);
    const traceBody = document.createElement("div");
    traceBody.className = "trace-body";
    trace.appendChild(traceBody);
    wrap.appendChild(trace);

    $messages.appendChild(wrap);
    wrap.scrollIntoView({ behavior: "smooth" });

    return { answer, traceBody };
}


function appendTrace(traceBody, type, payload) {
    const line = document.createElement("div");
    line.className = `trace-line ${type}`;

    if (type === "status") {
        line.textContent = `• ${payload.message}`;
    } else if (type === "iteration") {
        line.textContent = `— iteration ${payload.n} —`;
    } else if (type === "tool_call") {
        const args = JSON.stringify(payload.arguments);
        line.textContent = `→ ${payload.name}(${args})`;
    } else if (type === "tool_result") {
        const count = Array.isArray(payload.result) ? payload.result.length : 0;
        line.textContent = `← ${payload.name} returned ${count} hits`;

        if (Array.isArray(payload.result)) {
            const ul = document.createElement("ul");
            for (const hit of payload.result) {
                const li = document.createElement("li");
                li.textContent = `[${hit.id}] ${hit.question} (${hit.score})`;
                ul.appendChild(li);
            }
            line.appendChild(ul);
        }
    } else {
        line.textContent = `${type}: ${JSON.stringify(payload)}`;
    }

    traceBody.appendChild(line);
}


async function ask(question, course) {
    const { answer, traceBody } = addAssistantMessage();

    const response = await fetch("/api/ask", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        body: JSON.stringify({ question, course: course || null }),
    });

    if (!response.ok) {
        answer.textContent = `Error: ${response.status} ${response.statusText}`;
        return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const parts = buffer.split("\n\n");
        buffer = parts.pop();

        for (const part of parts) {
            const dataLine = part
                .split("\n")
                .find((l) => l.startsWith("data: "));
            if (!dataLine) continue;

            let payload;
            try {
                payload = JSON.parse(dataLine.slice(6));
            } catch {
                continue;
            }

            const { type, ...rest } = payload;

            if (type === "token") {
                answer.textContent += rest.delta;
            } else if (type === "done") {
                if (rest.answer) answer.textContent = rest.answer;
            } else {
                appendTrace(traceBody, type, rest);
            }
        }
    }
}


$form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const question = $question.value.trim();
    if (!question) return;

    addUserMessage(question);
    $question.value = "";
    $submit.disabled = true;

    try {
        await ask(question, $course.value);
    } catch (err) {
        console.error(err);
    } finally {
        $submit.disabled = false;
        $question.focus();
    }
});


loadCourses();
