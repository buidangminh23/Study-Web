let pyodidePromise = null;

function getPyodide() {
    if (!pyodidePromise) {
        pyodidePromise = loadPyodide();
    }
    return pyodidePromise;
}

async function saveAttempt(exercise, answer, score, result) {
    const response = await fetch(`/exercises/${exercise.dataset.exerciseId}/attempts`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({answer, score, result})
    });
    return response.json();
}

function setResult(exercise, message, passed) {
    const result = exercise.querySelector(".exercise-result");
    result.textContent = message;
    result.style.color = passed ? "#0f766e" : "#b91c1c";
}

document.querySelectorAll(".submit-answer").forEach((button) => {
    button.addEventListener("click", async () => {
        const exercise = button.closest(".exercise");
        let answer = "";
        if (exercise.dataset.type === "multiple_choice") {
            const selected = exercise.querySelector("input[type='radio']:checked");
            answer = selected ? selected.value : "";
        } else {
            answer = exercise.querySelector(".answer-input").value;
        }
        const data = await saveAttempt(exercise, answer, 0, "submitted");
        setResult(exercise, `${data.result} · ${Math.round(data.score)} points`, data.score >= 60);
    });
});

document.querySelectorAll(".run-code").forEach((button) => {
    button.addEventListener("click", async () => {
        const exercise = button.closest(".exercise");
        const state = exercise.querySelector(".runner-state");
        const output = exercise.querySelector(".code-output");
        const code = exercise.querySelector(".code-input").value;
        const testCode = exercise.querySelector(".test-code").value;
        state.textContent = "Loading Python runtime...";
        output.textContent = "";
        try {
            const pyodide = await getPyodide();
            state.textContent = "Running code...";
            pyodide.globals.set("user_code", code);
            pyodide.globals.set("test_code", testCode);
            const runner = `
import io
import contextlib
namespace = {}
stream = io.StringIO()
with contextlib.redirect_stdout(stream):
    exec(user_code, namespace)
output = stream.getvalue()
namespace["output"] = output
exec(test_code, namespace)
output
`;
            const result = await pyodide.runPythonAsync(runner);
            output.textContent = result || "No output.";
            const data = await saveAttempt(exercise, code, 100, "passed");
            setResult(exercise, `${data.result} · ${Math.round(data.score)} points`, true);
            state.textContent = "Finished.";
        } catch (error) {
            output.textContent = error.message;
            const data = await saveAttempt(exercise, code, 0, "failed");
            setResult(exercise, `${data.result} · ${Math.round(data.score)} points`, false);
            state.textContent = "Code did not pass the test.";
        }
    });
});
