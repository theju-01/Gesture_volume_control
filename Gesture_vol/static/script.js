let distanceChart;
let confidenceChart;

let distanceData = [];
let volumeData = [];
let volumeHistoryData = [];

window.onload = function () {


/* VOLUME vs DISTANCE GRAPH */

const ctx1 = document.getElementById('distanceChart').getContext('2d');

distanceChart = new Chart(ctx1, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Volume vs Distance',
            data: [],
            borderColor: '#a855f7',
            borderWidth: 2,
            tension: 0.3
        }]
    },
    options: {
        scales: {
            x: {
                title: { display: true, text: "Finger Distance" }
            },
            y: {
                beginAtZero: true,
                max: 100,
                title: { display: true, text: "Volume %" }
            }
        }
    }
});


/*  VOLUME HISTORY GRAPH  */

const ctx2 = document.getElementById('confidenceChart').getContext('2d');

confidenceChart = new Chart(ctx2, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Volume History',
            data: [],
            borderColor: '#22c55e',
            borderWidth: 2,
            tension: 0.3
        }]
    },
    options: {
        scales: {
            y: {
                beginAtZero: true,
                max: 100
            }
        }
    }
});


};

function updateData() {


fetch("/data")
    .then(response => response.json())
    .then(data => {

        document.getElementById("fps").innerText = data.fps;
        document.getElementById("hands").innerText = data.hands;
        document.getElementById("gesture").innerText = data.gesture;
        document.getElementById("emoji").innerText = data.emoji;
        document.getElementById("pinch").innerText = data.pinch;
        document.getElementById("distance-big").innerText = data.pinch;
        document.getElementById("latency").innerText = data.latency;

        const stateBox = document.getElementById("distance-state");
        stateBox.innerText = data.distance_state;

        if (data.distance_state === "Open") {
            stateBox.style.background = "green";
        }
        else if (data.distance_state === "Pinch") {
            stateBox.style.background = "orange";
        }
        else {
            stateBox.style.background = "red";
        }


        /*VOLUME BAR*/

        const volumeBar = document.getElementById("volume-level");
        const volumeValue = Math.max(0, Math.min(100, data.volume));

        volumeBar.style.width = volumeValue + "%";

        if (volumeValue <= 40) {
            volumeBar.style.background = "#22c55e";
        }
        else if (volumeValue <= 70) {
            volumeBar.style.background = "#f59e0b";
        }
        else {
            volumeBar.style.background = "#ef4444";
        }

        document.getElementById("volume-text").innerText = volumeValue + "%";


        /*  VOLUME vs DISTANCE GRAPH */

        if (distanceData.length > 50) {

            distanceData.shift();
            volumeData.shift();

            distanceChart.data.labels.shift();
            distanceChart.data.datasets[0].data.shift();
        }

        const graphDistance = data.pinch;
        const graphVolume = data.volume;

        distanceData.push(graphDistance);
        volumeData.push(graphVolume);

        distanceChart.data.labels.push(graphDistance);
        distanceChart.data.datasets[0].data.push(graphVolume);

        distanceChart.update();


        /* VOLUME HISTORY GRAPH */

        if (volumeHistoryData.length > 50) {

            volumeHistoryData.shift();
            confidenceChart.data.labels.shift();
            confidenceChart.data.datasets[0].data.shift();
        }

        volumeHistoryData.push(data.volume);

        confidenceChart.data.labels.push('');
        confidenceChart.data.datasets[0].data.push(data.volume);

        confidenceChart.update();


        /*DETECTION STATUS*/

        const status = document.getElementById("detect-status");
        const accuracyText = document.getElementById("accuracy");
        const accuracyBar = document.getElementById("accuracy-level");

        if (status && accuracyText && accuracyBar) {

            status.innerText = data.detection_status;
            accuracyText.innerText = data.accuracy;

            accuracyBar.style.width = data.accuracy + "%";

            if (data.accuracy > 80) {
                accuracyBar.style.background = "#22c55e";
            }
            else if (data.accuracy > 50) {
                accuracyBar.style.background = "#f59e0b";
            }
            else {
                accuracyBar.style.background = "#ef4444";
            }

        }

        const lockBox = document.getElementById("lock-state");

        if (lockBox) {

            if (data.lock_mode) {
                lockBox.innerText = "LOCKED";
                lockBox.style.background = "#ef4444";
            }
            else {
                lockBox.innerText = "UNLOCKED";
                lockBox.style.background = "#22c55e";
            }

        }

    });


}

setInterval(updateData, 100);

function updateCalibration() {


fetch('/update_calibration', {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
        min: document.getElementById("minPinch").value,
        max: document.getElementById("maxPinch").value,
        step: document.getElementById("volumeStep").value
    })
});


}
