// Get SVG overlay and image
const svg = document.getElementById('svg-overlay');
const mapImg = document.getElementById('map-image');
const units = window.units;  // use the global variable

function drawPolygons() {
    svg.innerHTML = '';
    const imgRect = mapImg.getBoundingClientRect();
    const imgWidth = mapImg.naturalWidth;
    const imgHeight = mapImg.naturalHeight;
    const scaleX = imgRect.width / imgWidth;
    const scaleY = imgRect.height / imgHeight;

    units.forEach(unit => {
        if (!unit.polygon || unit.polygon.length === 0) return;

        const points = unit.polygon.map(p => (p[0]*scaleX)+','+(p[1]*scaleY)).join(' ');
        const polygon = document.createElementNS('http://www.w3.org/2000/svg','polygon');
        polygon.setAttribute('points', points);
        polygon.classList.add('unit-polygon', unit.status);
        polygon.addEventListener('click', () => {
            window.location.href = '/unit/' + unit.id;
        });
        svg.appendChild(polygon);
    });
}

// redraw polygons on image load and window resize
mapImg.addEventListener('load', drawPolygons);
window.addEventListener('resize', drawPolygons);
if (mapImg.complete) drawPolygons();
