<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Parco Tassino — Radar</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
  <style>
    body {
      margin: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      background: #F5F2EE;
      font-family: 'Inter', sans-serif;
    }
    canvas {
      max-width: 560px;
      max-height: 560px;
    }
  </style>
</head>
<body>
  <canvas id="radar"></canvas>

  <script>
    const data = {
      labels: [
        'Emotional',
        'Sensory',
        'Action',
        'Infrastructure',
        'Relational',
        'Tension',
      ],
      values: [38.8, 19.6, 14.5, 13.7, 10.3, 3.2],
      colors: ['#9370DB', '#40C878', '#3790EB', '#E89832', '#EBD028', '#DC3450'],
    };

    const pointColors = data.colors;

    new Chart(document.getElementById('radar'), {
      type: 'radar',
      data: {
        labels: data.labels,
        datasets: [{
          data: data.values,
          fill: true,
          backgroundColor: 'rgba(123, 94, 167, 0.12)',
          borderColor: 'rgba(123, 94, 167, 0.7)',
          borderWidth: 2,
          pointBackgroundColor: pointColors,
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          pointRadius: 6,
          pointHoverRadius: 8,
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => ` ${ctx.raw}%`
            }
          }
        },
        scales: {
          r: {
            min: 0,
            max: 45,
            ticks: {
              stepSize: 10,
              callback: v => v + '%',
              font: { size: 10 },
              color: '#999690',
              backdropColor: 'transparent',
            },
            grid: {
              color: 'rgba(0,0,0,0.08)',
            },
            angleLines: {
              color: 'rgba(0,0,0,0.10)',
            },
            pointLabels: {
              font: { size: 13, weight: '500' },
              color: '#3A3835',
            },
          }
        }
      }
    });
  </script>
</body>
</html>