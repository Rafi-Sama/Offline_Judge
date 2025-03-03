var socket = io.connect('http://' + document.domain + ':' + location.port);

socket.on('update_leaderboard', function(data) {
    var tbody = document.querySelector('#leaderboard-table tbody');
    tbody.innerHTML = '';
    data.standings.forEach(function(entry, index) {
        var row = `<tr><td>${index + 1}</td><td>${entry.username}</td><td>${entry.solved}</td></tr>`;
        tbody.innerHTML += row;
    });
});

document.getElementById('add-test-case').addEventListener('click', function () {
    let container = document.getElementById('test-cases-container');
    let testCaseCount = container.getElementsByClassName('test-case').length;
    let newTestCase = document.createElement('div');
    newTestCase.classList.add('test-case', 'mt-4');
    newTestCase.innerHTML = `
        <label class="text-gray-300">Test Input</label>
        <textarea name="input[]" rows="3" class="w-full p-3 rounded-lg bg-gray-900 text-gray-300 border border-gray-700 focus:ring-2 focus:ring-blue-500 transition"></textarea>
        <label class="text-gray-300">Expected Output</label>
        <textarea name="output[]" rows="3" class="w-full p-3 rounded-lg bg-gray-900 text-gray-300 border border-gray-700 focus:ring-2 focus:ring-blue-500 transition"></textarea>
        <label class="text-gray-300 flex items-center"><input type="checkbox" name="sample[]" value="${testCaseCount}" class="mr-2"> Mark as Sample Test Case</label>
    `;
    container.appendChild(newTestCase);
});

document.getElementById('add-test-case').addEventListener('click', function () {
    let container = document.getElementById('test-cases-container');
    let newTestCase = document.createElement('div');
    newTestCase.classList.add('test-case', 'mt-4');
    newTestCase.innerHTML = `
        <label class="text-gray-300">Test Input</label>
        <textarea name="input[]" rows="3" class="w-full p-3 rounded-lg bg-gray-900 text-gray-300 border border-gray-700 focus:ring-2 focus:ring-blue-500 transition"></textarea>
        <label class="text-gray-300">Expected Output</label>
        <textarea name="output[]" rows="3" class="w-full p-3 rounded-lg bg-gray-900 text-gray-300 border border-gray-700 focus:ring-2 focus:ring-blue-500 transition"></textarea>
        <label class="text-gray-300 flex items-center">
            <input type="checkbox" name="sample[]" class="mr-2"> Mark as Sample Test Case
        </label>`;
    container.appendChild(newTestCase);
});

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".countdown").forEach(el => {
        let startTime = el.dataset.start * 1000;
        let contestItem = el.closest(".contest-item");
        let enterButton = contestItem?.querySelector(".enter-button");

        let updateCountdown = () => {
            let timeLeft = startTime - Date.now();
            if (timeLeft > 0) {
                let h = Math.floor(timeLeft / 3600000),
                    m = Math.floor((timeLeft % 3600000) / 60000),
                    s = Math.floor((timeLeft % 60000) / 1000);
                el.innerText = `Starts in: ${h}h ${m}m ${s}s`;
            } else {
                el.innerText = "Contest Started!";
                clearInterval(interval);
                if (enterButton) setTimeout(() => window.location.href = enterButton.href, 1000);
            }
        };

        let interval = setInterval(updateCountdown, 1000);
        updateCountdown();
    });
});

document.getElementById("run-button").addEventListener("click", async function() {
    let code = document.querySelector("textarea[name='code']").value;
    let language = document.querySelector("select[name='language']").value;
    let problemId = "{{ problem.id }}";

    try {
        let response = await fetch(`/problem/${problemId}/run`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: `code=${encodeURIComponent(code)}&language=${language}`
        });

        let data = await response.json();
        let resultDiv = document.getElementById("run-results");
        resultDiv.innerHTML = `<p><strong>Status:</strong> ${data.status}</p>`;

        if (data.results) {
            data.results.forEach(test => {
                resultDiv.innerHTML += `
                    <div class="p-4 border border-gray-700 rounded-lg mt-3">
                        <p><strong>Input:</strong> ${test.input}</p>
                        <p><strong>Expected:</strong> ${test.expected}</p>
                        <p><strong>Output:</strong> ${test.output}</p>
                        <p><strong>Status:</strong> ${test.status}</p>
                    </div>
                `;
            });
        }
    } catch (error) {
        console.error("Error:", error);
    }
});

function validateEmail() {
    toggleError("email", /^[^\s@]+@[^\s@]+\.[^\s@]+$/);
}
function validatePassword() {
    toggleError("password", /^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$/);
}
function validateConfirmPassword() {
    toggleError("confirm_password", document.getElementById("password").value === document.getElementById("confirm_password").value);
}
function toggleError(field, condition) {
    document.getElementById(`${field}-error`).classList.toggle("hidden", typeof condition === "boolean" ? condition : condition.test(document.getElementById(field).value));
}
function validateForm() {
    validateEmail(); validatePassword(); validateConfirmPassword();
    return !document.querySelector(".error-message:not(.hidden)");
}

function toggleSubmissions() {
    let url = new URL(window.location.href);
    url.searchParams.set("mine", document.getElementById("mineOnly").checked);
    window.location.href = url.toString();
}

function openModal(id, code, lang) {
    document.getElementById("modalTitle").textContent = `Submission #${id} (${lang})`;
    document.getElementById("modalCode").textContent = code;
    document.getElementById("codeModal").classList.remove("hidden");
}

function closeModal() {
    document.getElementById("codeModal").classList.add("hidden");
}

function copyCode() {
    navigator.clipboard.writeText(document.getElementById("modalCode").textContent).then(() => {
        let confirmation = document.getElementById("copyConfirmation");
        confirmation.classList.remove("hidden");
        setTimeout(() => confirmation.classList.add("hidden"), 1500);
    });
}