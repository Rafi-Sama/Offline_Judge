var socket = io.connect('http://' + document.domain + ':' + location.port);

socket.on('update_leaderboard', function(data) {
    var tbody = document.querySelector('#leaderboard-table tbody');
    tbody.innerHTML = '';
    data.standings.forEach(function(entry, index) {
        var row = `<tr><td>${index + 1}</td><td>${entry.username}</td><td>${entry.solved}</td></tr>`;
        tbody.innerHTML += row;
    });
});