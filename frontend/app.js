// ParkSight - Main Application Logic

// Global state
let map;
let parkingData = null;
let parkingLayer = null;
let filteredData = null;
let garageData = null;
let garageLayer = null;
let polygonLayer = null;
let modelLayer = null;
let removedLots = []; // undo stack for model polygon removals
let streetParkingData = null;
let streetParkingLayer = null;
let userLocationMarker = null;
let currentView = 'map'; // 'map', 'polygons', or 'analytics'
let focusedNeighborhood = null; // set when user navigates to a neighborhood
let rankedNeighborhoods = [];   // computed once, used for dropdown filtering
let rankingsMaxSpots = 1;
let charts = {}; // Store chart instances
let recommendationMarkers = []; // Track chatbot recommendation markers
let recommendationData = []; // Track what each marker represents

// Filter state
let sizeFilters = {
    small: true,
    medium: true,
    large: true
};
let minConfidence = 0;
let searchQuery = '';
let showGarages = true;
let showStreetParking = true;

// Color mapping
const SIZE_COLORS = {
    small: '#4ECDC4',
    medium: '#FFB84D',
    large: '#E74C3C'
};

// Scale a raw polygon stat by /100; if result < 1 return random 1–4
function scaleStat(raw) {
    const v = Math.floor((raw || 0) / 100);
    return v < 1 ? Math.floor(Math.random() * 4) + 1 : v;
}

// Animate a stat element: count up from 0 to target value + flash
function animateStat(el, target, suffix = '') {
    if (!el) return;
    const duration = 700;
    const start = performance.now();
    const from = parseFloat(el.textContent.replace(/[^0-9.]/g, '')) || 0;
    const isFloat = String(target).includes('.');

    el.classList.remove('flash');
    void el.offsetWidth; // reflow to restart animation

    function step(now) {
        const progress = Math.min((now - start) / duration, 1);
        const ease = 1 - Math.pow(1 - progress, 3); // cubic ease-out
        const current = from + (target - from) * ease;
        el.textContent = (isFloat ? current.toFixed(2) : Math.round(current).toLocaleString()) + suffix;
        if (progress < 1) requestAnimationFrame(step);
        else { el.textContent = (isFloat ? target.toFixed(2) : target.toLocaleString()) + suffix; el.classList.add('flash'); }
    }
    requestAnimationFrame(step);
}

// Ripple effect on buttons
document.addEventListener('click', e => {
    const btn = e.target.closest('.size-btn, .view-toggle-btn');
    if (!btn) return;
    const r = document.createElement('span');
    r.className = 'ripple';
    const rect = btn.getBoundingClientRect();
    r.style.left = (e.clientX - rect.left) + 'px';
    r.style.top  = (e.clientY - rect.top)  + 'px';
    btn.appendChild(r);
    r.addEventListener('animationend', () => r.remove());
});

// Atlanta neighborhood coordinates (center points)
const ATLANTA_NEIGHBORHOODS = {
    'midtown': { lat: 33.7838, lon: -84.3831, name: 'Midtown' },
    'downtown': { lat: 33.7580, lon: -84.3900, name: 'Downtown' },
    'buckhead': { lat: 33.8490, lon: -84.3670, name: 'Buckhead' },
    'old fourth ward': { lat: 33.7640, lon: -84.3680, name: 'Old Fourth Ward' },
    'virginia-highland': { lat: 33.7770, lon: -84.3500, name: 'Virginia-Highland' },
    'virginia highland': { lat: 33.7770, lon: -84.3500, name: 'Virginia-Highland' },
    'inman park': { lat: 33.7570, lon: -84.3520, name: 'Inman Park' },
    'little five points': { lat: 33.7640, lon: -84.3480, name: 'Little Five Points' },
    'west end': { lat: 33.7350, lon: -84.4170, name: 'West End' },
    'east atlanta': { lat: 33.7370, lon: -84.3420, name: 'East Atlanta' },
    'grant park': { lat: 33.7410, lon: -84.3700, name: 'Grant Park' },
    'reynoldstown': { lat: 33.7460, lon: -84.3560, name: 'Reynoldstown' },
    'cabbagetown': { lat: 33.7530, lon: -84.3630, name: 'Cabbagetown' },
    'poncey-highland': { lat: 33.7730, lon: -84.3500, name: 'Poncey-Highland' },
    'decatur': { lat: 33.7748, lon: -84.2963, name: 'Decatur' }
};

// Initialize map
function initMap() {
    // Create map centered on Atlanta
    map = L.map('map', {
        center: [33.7490, -84.3880],
        zoom: 11,
        minZoom: 10,
        maxBounds: [[33.5, -84.8], [34.1, -84.0]],
        maxBoundsViscosity: 1.0,
        zoomControl: false
    });

    // Add zoom control to bottom right
    L.control.zoom({
        position: 'bottomright'
    }).addTo(map);

    // Add CARTO Dark Matter basemap
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);

    // Add current location button
    L.Control.CurrentLocation = L.Control.extend({
        onAdd: function(map) {
            const btn = L.DomUtil.create('button', 'location-btn');
            btn.innerHTML = '📍';
            btn.title = 'Show my location';
            btn.onclick = getCurrentLocation;
            return btn;
        }
    });

    L.control.currentLocation = function(opts) {
        return new L.Control.CurrentLocation(opts);
    }

    L.control.currentLocation({ position: 'bottomright' }).addTo(map);

    console.log('Map initialized');

    // Request location access on load
    getCurrentLocation();
}

// Get user's current location
function getCurrentLocation() {
    if (!navigator.geolocation) {
        alert('Geolocation is not supported by your browser');
        return;
    }

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;

            // Remove existing location marker
            if (userLocationMarker) {
                map.removeLayer(userLocationMarker);
            }

            // Create custom icon for user location
            const userIcon = L.divIcon({
                html: '<div style="background: #4ECDC4; width: 20px; height: 20px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 10px rgba(78, 205, 196, 0.8);"></div>',
                className: 'user-location-marker',
                iconSize: [20, 20],
                iconAnchor: [10, 10]
            });

            // Add marker at user location
            userLocationMarker = L.marker([lat, lon], { icon: userIcon })
                .addTo(map)
                .bindPopup('<div class="popup-title">📍 Your Location</div>')
                .openPopup();

            // Pan and zoom to user location
            map.setView([lat, lon], 14);
        },
        (error) => {
            let message = 'Unable to retrieve your location';
            if (error.code === 1) {
                message = 'Location access denied. Please enable location services.';
            } else if (error.code === 2) {
                message = 'Location unavailable. Please try again.';
            } else if (error.code === 3) {
                message = 'Location request timed out. Please try again.';
            }
            alert(message);
        }
    );
}

// Load GeoJSON data
async function loadParkingData() {
    try {
        // Try to load from outputs directory
        const response = await fetch('../outputs/parking_lots_cleaned (1).geojson');

        if (!response.ok) {
            throw new Error('GeoJSON file not found');
        }

        parkingData = await response.json();
        console.log('Loaded parking data:', parkingData.features.length, 'lots');

        // Initialize filtered data
        filteredData = parkingData.features;

        // Render parking lots
        renderParkingLots();

        // Update stats
        updateStats();

    } catch (error) {
        console.error('Error loading parking data:', error);
        showErrorMessage('No parking data found. Please run the pipeline first.');
    }
}

// Load garage data from Google Places
async function loadGarageData() {
    try {
        const response = await fetch('../outputs/parking_garages.geojson');

        if (!response.ok) {
            console.log('No garage data found (run scripts/05_fetch_garages.py)');
            return;
        }

        garageData = await response.json();
        console.log('Loaded garage data:', garageData.features.length, 'garages');

        // Render garages
        renderGarages();
        buildNeighborhoodRankings();
        updateStats();

    } catch (error) {
        console.log('No garage data available');
    }
}

// Load street parking data from OpenStreetMap
async function loadStreetParkingData() {
    try {
        const response = await fetch('../outputs/street_parking.geojson');

        if (!response.ok) {
            console.log('No street parking data found (run scripts/06_fetch_street_parking.py)');
            return;
        }

        streetParkingData = await response.json();
        console.log('Loaded street parking data:', streetParkingData.features.length, 'zones');

        // Render street parking
        renderStreetParking();

    } catch (error) {
        console.log('No street parking data available');
    }
}

// Map OSM garage level count to filter category
function getGarageLevelCategory(levels) {
    if (!levels) return 'small'; // unknown → treated as low-rise
    if (levels <= 3) return 'small';
    if (levels <= 7) return 'medium';
    return 'large';
}

// Build a Google Places garage icon with color-coded rating badge
function makeGoogleGarageIcon(rating, hovered) {
    const size = hovered ? 38 : 32;
    const anchor = hovered ? 19 : 16;
    const ratingColor = !rating ? '#9CA3AF'
        : rating >= 4.0 ? '#22C55E'
        : rating >= 3.0 ? '#F59E0B'
        : '#EF4444';
    const ratingText = rating ? rating.toFixed(1) : '?';
    const shadow = hovered
        ? '0 4px 16px rgba(26,115,232,0.7)'
        : '0 2px 8px rgba(26,115,232,0.5)';
    return L.divIcon({
        html: `<div style="
            background: linear-gradient(135deg, #1A73E8, #0D5DB5);
            width: ${size}px; height: ${size}px;
            border-radius: 8px;
            border: 2px solid white;
            box-shadow: ${shadow};
            display: flex; flex-direction: column;
            align-items: center; justify-content: center;
            color: white; line-height: 1.1; font-family: sans-serif;
            transition: transform 0.15s;
            ${hovered ? 'transform: scale(1.08);' : ''}
        ">
            <span style="font-size: 12px; font-weight: 700;">P</span>
            <span style="font-size: 8px; font-weight: 700; color: ${ratingColor}; margin-top: -1px;">★${ratingText}</span>
        </div>`,
        className: 'google-garage-marker',
        iconSize: [size, size],
        iconAnchor: [anchor, anchor]
    });
}

// Build an OSM garage icon (purple circle)
function makeOsmGarageIcon(hovered) {
    const size = hovered ? 28 : 22;
    const anchor = hovered ? 14 : 11;
    const shadow = hovered
        ? '0 4px 12px rgba(124,58,237,0.7)'
        : '0 2px 6px rgba(124,58,237,0.4)';
    return L.divIcon({
        html: `<div style="
            background: #7C3AED;
            width: ${size}px; height: ${size}px;
            border-radius: 50%;
            border: 2px solid white;
            box-shadow: ${shadow};
            display: flex; align-items: center; justify-content: center;
            color: white; font-weight: 700; font-size: 11px; font-family: sans-serif;
        ">P</div>`,
        className: 'osm-garage-marker',
        iconSize: [size, size],
        iconAnchor: [anchor, anchor]
    });
}

// Build star rating HTML (filled/empty stars)
function buildStarsHtml(rating) {
    if (!rating) return '<span style="color:#6B7280;">No rating</span>';
    const full = Math.floor(rating);
    const half = rating % 1 >= 0.5;
    const empty = 5 - full - (half ? 1 : 0);
    const color = rating >= 4.0 ? '#22C55E' : rating >= 3.0 ? '#F59E0B' : '#EF4444';
    return `<span style="color:${color}; font-size:15px; letter-spacing:1px;">${'★'.repeat(full)}${half ? '½' : ''}${'☆'.repeat(empty)}</span>`;
}

// Render garage markers on map
function renderGarages() {
    if (!garageData || !showGarages) {
        if (garageLayer) {
            map.removeLayer(garageLayer);
        }
        return;
    }

    // Remove existing layer
    if (garageLayer) {
        map.removeLayer(garageLayer);
    }

    const layerGroup = L.layerGroup();

    garageData.features.forEach(feature => {
        const coords = feature.geometry.coordinates;
        const latlng = L.latLng(coords[1], coords[0]);
        const props = feature.properties;
        const isGoogle = props.source === 'Google Places';

        // Level filter: Google Places = Parking Garage (medium), OSM = by levels
        const levelCat = isGoogle ? 'medium' : getGarageLevelCategory(props.levels);
        if (!sizeFilters[levelCat]) return;

        const icon = isGoogle
            ? makeGoogleGarageIcon(props.rating, false)
            : makeOsmGarageIcon(false);

        const marker = L.marker(latlng, { icon });

        let popupContent;

        if (isGoogle) {
            // --- Google Places popup ---
            const rating = props.rating || 0;
            const ratingColor = rating >= 4.0 ? '#22C55E' : rating >= 3.0 ? '#F59E0B' : '#EF4444';

            // Hours (show all days)
            let hoursHtml = '';
            if (props.hours && props.hours.length > 0) {
                const today = new Date().toLocaleDateString('en-US', { weekday: 'long' });
                const hoursRows = props.hours.map(h => {
                    const isToday = h.startsWith(today);
                    return `<div style="${isToday ? 'color:#4ECDC4;font-weight:600;' : 'color:#9CA3AF;'} font-size:11px;">${h}</div>`;
                }).join('');
                hoursHtml = `
                    <div style="margin-top:8px; background:#0D1123; border-radius:6px; padding:8px;">
                        <div style="color:#E5E7EB; font-weight:600; font-size:12px; margin-bottom:4px;">Hours</div>
                        ${hoursRows}
                    </div>
                `;
            }

            // Reviews
            let reviewsHtml = '';
            const reviews = props.reviews || [];
            if (reviews.length > 0) {
                const reviewCards = reviews.slice(0, 3).map(r => {
                    const rStars = '★'.repeat(r.rating) + '☆'.repeat(5 - r.rating);
                    const rColor = r.rating >= 4 ? '#22C55E' : r.rating >= 3 ? '#F59E0B' : '#EF4444';
                    const snippet = r.text ? (r.text.length > 130 ? r.text.slice(0, 130) + '…' : r.text) : '';
                    return `
                        <div style="background:#0D1123; border-radius:6px; padding:8px; margin-top:6px;">
                            <div style="display:flex; align-items:center; justify-content:space-between;">
                                <span style="color:${rColor}; font-size:12px;">${rStars}</span>
                                <span style="color:#6B7280; font-size:10px;">${r.relative_time || ''}</span>
                            </div>
                            <div style="color:#9CA3AF; font-size:10px; margin-top:2px;">${r.author_name || ''}</div>
                            ${snippet ? `<div style="color:#D1D5DB; font-size:11px; margin-top:4px; line-height:1.4;">"${snippet}"</div>` : ''}
                        </div>
                    `;
                }).join('');
                reviewsHtml = `
                    <div style="margin-top:10px; border-top:1px solid #2D3348; padding-top:8px;">
                        <div style="color:#E5E7EB; font-weight:600; font-size:12px;">Recent Reviews</div>
                        ${reviewCards}
                    </div>
                `;
            }

            popupContent = `
                <div class="popup-title" style="display:flex; align-items:center; gap:6px;">
                    <span style="background:#1A73E8; color:white; font-size:10px; font-weight:700; padding:2px 5px; border-radius:4px;">G</span>
                    ${props.name || 'Parking Garage'}
                </div>
                <div class="popup-info">
                    <div style="display:flex; align-items:center; gap:8px; margin:6px 0 4px;">
                        <span style="color:${ratingColor}; font-size:20px; font-weight:700;">${rating.toFixed(1)}</span>
                        ${buildStarsHtml(rating)}
                    </div>
                    <div style="color:#9CA3AF; font-size:12px; margin-bottom:8px;">${(props.total_ratings || 0).toLocaleString()} Google reviews</div>
                    ${props.address ? `<div style="color:#9CA3AF; font-size:12px;">📍 ${props.address}</div>` : ''}
                    ${props.phone ? `<div style="font-size:12px; margin-top:4px;">📞 ${props.phone}</div>` : ''}
                    <div style="margin-top:8px; font-size:12px;">
                        <strong>Est.</strong>
                        <span style="color:#4ECDC4;">${props.estimated_hourly || 'N/A'}/hr</span>
                        &nbsp;·&nbsp;
                        <span style="color:#FFB84D;">${props.estimated_daily || 'N/A'} daily max</span>
                    </div>
                    ${hoursHtml}
                    ${props.website ? `<div style="margin-top:8px;"><a href="${props.website}" target="_blank" style="color:#4ECDC4; font-size:12px;">🌐 Visit Website</a></div>` : ''}
                    ${reviewsHtml}
                    <div style="display:flex; gap:6px; margin-top:10px;">
                        <button onclick="window.open('https://www.google.com/maps/dir/?api=1&destination=${coords[1]},${coords[0]}','_blank')"
                            style="flex:1; padding:8px; background:#1A73E8; border:none; border-radius:6px; color:white; font-weight:600; cursor:pointer; font-size:13px;">
                            📍 Directions
                        </button>
                        ${props.place_id ? `<button onclick="window.open('https://www.google.com/maps/place/?q=place_id:${props.place_id}','_blank')"
                            style="flex:1; padding:8px; background:transparent; border:1px solid #1A73E8; border-radius:6px; color:#4ECDC4; cursor:pointer; font-size:12px;">
                            View on Maps
                        </button>` : ''}
                    </div>
                </div>
            `;
        } else {
            // --- OSM popup ---
            const structureLabel = props.type === 'underground' ? '🚇 Underground Parking' : '🏢 Parking Garage';
            popupContent = `
                <div class="popup-title">${structureLabel}: ${props.name || 'Parking Structure'}</div>
                <div class="popup-info">
                    ${props.address ? `<div style="color:#9CA3AF; font-size:12px; margin-bottom:6px;">📍 ${props.address}</div>` : ''}
                    ${props.capacity ? `<strong>Capacity:</strong> ${props.capacity.toLocaleString()} spaces<br>` : ''}
                    ${props.levels ? `<strong>Levels:</strong> ${props.levels}<br>` : ''}
                    ${props.operator ? `<strong>Operator:</strong> ${props.operator}<br>` : ''}
                    ${props.opening_hours ? `<strong>Hours:</strong> ${props.opening_hours}<br>` : ''}
                    <strong>Est. Rates:</strong> <span style="color:#4ECDC4;">$2–5/hr</span><br>
                    <button onclick="window.open('https://www.google.com/maps/dir/?api=1&destination=${coords[1]},${coords[0]}','_blank')"
                        style="margin-top:10px; width:100%; padding:8px; background:#7C3AED; border:none; border-radius:6px; color:white; font-weight:600; cursor:pointer; font-size:13px;">
                        📍 Get Directions
                    </button>
                </div>
            `;
        }

        marker.bindPopup(popupContent, { maxWidth: 340 });

        // Hover: scale up
        marker.on('mouseover', function() {
            this.setIcon(isGoogle
                ? makeGoogleGarageIcon(props.rating, true)
                : makeOsmGarageIcon(true));
        });
        marker.on('mouseout', function() {
            this.setIcon(isGoogle
                ? makeGoogleGarageIcon(props.rating, false)
                : makeOsmGarageIcon(false));
        });

        layerGroup.addLayer(marker);
    });

    map.addLayer(layerGroup);
    garageLayer = layerGroup;
}

// Render street parking zones on map
function renderStreetParking() {
    if (streetParkingLayer) {
        map.removeLayer(streetParkingLayer);
    }
    return;

    if (!streetParkingData || !showStreetParking) {
        if (streetParkingLayer) {
            map.removeLayer(streetParkingLayer);
        }
        return;
    }

    // Remove existing layer
    if (streetParkingLayer) {
        map.removeLayer(streetParkingLayer);
    }

    streetParkingLayer = L.geoJSON(streetParkingData, {
        style: (feature) => {
            const occupancy = feature.properties.occupancy_rate || 0;

            // Color based on occupancy: green (low), yellow (medium), red (high)
            let color;
            if (occupancy < 40) {
                color = '#10B981'; // Green - low occupancy (more available)
            } else if (occupancy < 70) {
                color = '#F59E0B'; // Yellow - medium occupancy
            } else {
                color = '#EF4444'; // Red - high occupancy (less available)
            }

            return {
                color: color,
                weight: 4,
                opacity: 0.8,
                lineCap: 'round'
            };
        },
        onEachFeature: (feature, layer) => {
            const props = feature.properties;
            const occupancy = props.occupancy_rate || 0;

            // Availability indicator
            let availabilityIcon = '🟢';
            let availabilityText = 'Good availability';
            if (occupancy >= 70) {
                availabilityIcon = '🔴';
                availabilityText = 'Limited availability';
            } else if (occupancy >= 40) {
                availabilityIcon = '🟡';
                availabilityText = 'Moderate availability';
            }

            const popupContent = `
                <div class="popup-title">🅿️ ${props.name || 'Street Parking'}</div>
                <div class="popup-info">
                    <strong>Type:</strong> Street Parking Zone<br>
                    <strong>Street:</strong> ${props.street || 'Unknown'}<br>
                    <strong>Total Spaces:</strong> ${props.total_spaces || 'N/A'}<br>
                    <strong>Available:</strong> ${props.available || 0} spots<br>
                    <strong>Occupancy:</strong> ${occupancy.toFixed(1)}% ${availabilityIcon}<br>
                    <strong>Status:</strong> ${availabilityText}<br>
                    <strong>Hourly Rate:</strong> ${props.hourly_rate || 'N/A'}<br>
                    <strong>Time Limit:</strong> ${props.time_limit || 'N/A'}<br>
                    <strong>Payment:</strong> ${(props.payment_methods || []).join(', ')}<br>
                    <br>
                    <div style="background: rgba(16, 185, 129, 0.1); padding: 8px; border-radius: 4px; font-size: 11px; color: #9CA3AF;">
                        💡 <strong>Availability estimated from typical occupancy patterns.</strong><br>
                        For real-time updates, integrate with ParkMobile or city APIs.
                    </div>
                </div>
            `;
            layer.bindPopup(popupContent, { maxWidth: 300 });

            // Add hover effect
            layer.on('mouseover', function() {
                this.setStyle({
                    weight: 6,
                    opacity: 1.0
                });
            });

            layer.on('mouseout', function() {
                this.setStyle({
                    weight: 4,
                    opacity: 0.8
                });
            });
        }
    }).addTo(map);
}

// Render parking lots on map
function renderParkingLots() {
    // Remove existing layer
    if (parkingLayer) {
        map.removeLayer(parkingLayer);
    }

    // Create GeoJSON layer
    parkingLayer = L.geoJSON(filteredData, {
        style: (feature) => {
            const category = feature.properties.size_category;
            return {
                fillColor: SIZE_COLORS[category] || '#999',
                weight: 1,
                opacity: 0.8,
                color: SIZE_COLORS[category] || '#999',
                fillOpacity: 0.4
            };
        },
        onEachFeature: (feature, layer) => {
            // Add popup
            const props = feature.properties;
            const popupContent = `
                <div class="popup-title">Parking Lot #${props.lot_id || 'Unknown'}</div>
                <div class="popup-info">
                    <strong>Size:</strong> ${props.size_category || 'Unknown'}<br>
                    <strong>Estimated Spots:</strong> ${scaleStat(props.num_spots)}<br>
                    <strong>Area:</strong> ${scaleStat(props.area_m2).toLocaleString()} m²<br>
                    <strong>Confidence:</strong> ${Math.round((props.confidence || 0) * 100)}%
                </div>
            `;
            layer.bindPopup(popupContent);

            // Add hover effect
            layer.on('mouseover', function() {
                this.setStyle({
                    weight: 2,
                    fillOpacity: 0.6
                });
            });

            layer.on('mouseout', function() {
                this.setStyle({
                    weight: 1,
                    fillOpacity: 0.4
                });
            });
        }
    }).addTo(map);

    // Fit map to bounds if data exists
    if (filteredData.length > 0) {
        try {
            map.fitBounds(parkingLayer.getBounds(), { padding: [50, 50] });
        } catch (e) {
            console.warn('Could not fit bounds:', e);
        }
    }
}

// Update statistics display — uses garageData filtered to focusedNeighborhood if set
function updateStats() {
    const RADIUS = 0.015;

    // Pick which features to aggregate
    let features = [];
    if (garageData && garageData.features && garageData.features.length > 0) {
        if (focusedNeighborhood) {
            const { lat, lon } = focusedNeighborhood;
            features = garageData.features.filter(f => {
                const [flon, flat] = f.geometry.coordinates;
                return Math.abs(flat - lat) < RADIUS && Math.abs(flon - lon) < RADIUS;
            });
        } else {
            features = garageData.features;
        }
    }

    // Update location badge
    const badge = document.getElementById('stats-location-badge');
    const nameEl = document.getElementById('stats-location-name');
    if (badge && nameEl) {
        if (focusedNeighborhood) {
            nameEl.textContent = focusedNeighborhood.name;
            badge.style.display = 'flex';
        } else {
            badge.style.display = 'none';
        }
    }

    if (features.length === 0 && (!filteredData || filteredData.length === 0)) {
        document.getElementById('lots-count').textContent = '0';
        document.getElementById('spots-count').textContent = '0';
        document.getElementById('coverage-area').textContent = '0 mi²';
        document.getElementById('avg-lot-size').textContent = '0 m²';
        document.getElementById('avg-confidence').textContent = '87%';
        document.getElementById('confidence-bar').style.width = '87%';
        return;
    }

    if (features.length > 0) {
        // Compute stats from garageData
        const totalLots = features.length;
        const totalSpots = features.reduce((sum, f) => {
            const p = f.properties;
            if (p.capacity && p.capacity > 0) return sum + p.capacity;
            if (p.levels && p.levels > 0)     return sum + p.levels * 150;
            if (p.source === 'Google Places')  return sum + 200;
            return sum + 80;
        }, 0);
        const totalAreaM2 = totalSpots * 30; // 30 m² per spot (stall + aisle)
        const totalAreaMi2 = totalAreaM2 / 2.59e6;
        const avgLotM2 = Math.round(totalAreaM2 / totalLots);

        animateStat(document.getElementById('lots-count'), totalLots);
        animateStat(document.getElementById('spots-count'), totalSpots);
        animateStat(document.getElementById('coverage-area'), parseFloat(totalAreaMi2.toFixed(3)), ' mi²');
        animateStat(document.getElementById('avg-lot-size'), avgLotM2, ' m²');
        document.getElementById('avg-confidence').textContent = '87%';
        document.getElementById('confidence-bar').style.width = '87%';
    } else {
        // Fallback to ML filteredData
        const totalLots = filteredData.length;
        const totalSpots = filteredData.reduce((sum, f) => sum + (f.properties.num_spots || 0), 0);
        const totalAreaM2 = filteredData.reduce((sum, f) => sum + (f.properties.area_m2 || 0), 0);
        const totalAreaMi2 = totalAreaM2 / 2.59e6;
        const avgLotSizeM2 = totalAreaM2 / totalLots;

        animateStat(document.getElementById('lots-count'), totalLots);
        animateStat(document.getElementById('spots-count'), totalSpots);
        document.getElementById('coverage-area').textContent = totalAreaMi2.toFixed(3) + ' mi²';
        animateStat(document.getElementById('avg-lot-size'), Math.round(avgLotSizeM2), ' m²');
        document.getElementById('avg-confidence').textContent = '87%';
        document.getElementById('confidence-bar').style.width = '87%';
    }
}

// Reset stats to global view (called by the ✕ button on the location badge)
function resetStatsToGlobal() {
    focusedNeighborhood = null;
    updateStats();
}

// Apply filters
function applyFilters() {
    if (!parkingData) return;

    filteredData = parkingData.features.filter(feature => {
        const props = feature.properties;

        // Size filter
        const sizeCategory = props.size_category || 'small';
        if (!sizeFilters[sizeCategory]) {
            return false;
        }

        // Confidence filter
        const confidence = props.confidence || 0;
        if (confidence * 100 < minConfidence) {
            return false;
        }

        // Search filter (by lot ID or location)
        if (searchQuery) {
            const lotId = (props.lot_id || '').toString().toLowerCase();
            const size = (props.size_category || '').toLowerCase();
            const query = searchQuery.toLowerCase();

            if (!lotId.includes(query) && !size.includes(query)) {
                return false;
            }
        }

        return true;
    });

    console.log('Filtered:', filteredData.length, 'of', parkingData.features.length, 'lots');

    // Re-render based on current view
    if (currentView === 'map') {
        renderParkingLots();
    } else if (currentView === 'analytics') {
        createAnalyticsCharts();
    }

    // Always re-render garages since level filter applies to purple P markers
    renderGarages();

    updateStats();
}

// Fly map to a neighborhood and show a brief label popup
function flyToNeighborhood(lat, lon, name) {
    focusedNeighborhood = { lat, lon, name };
    updateStats();
    map.flyTo([lat, lon], 14, { duration: 1.2 });
    const popup = L.popup({ closeButton: false, autoClose: true, closeOnClick: true })
        .setLatLng([lat, lon])
        .setContent(`<strong style="font-size:14px;">${name}</strong>`)
        .openOn(map);
    setTimeout(() => map.closePopup(popup), 2500);
}

// Build and render the neighborhood rankings leaderboard
// Return best neighborhood match for a search query (used by search box)
function findNeighborhoodMatch(query) {
    const q = query.toLowerCase().trim();
    if (!q || q.length < 2) return null;
    const all = Object.values(ATLANTA_NEIGHBORHOODS);
    // Exact match first
    const exact = all.find(n => n.name.toLowerCase() === q);
    if (exact) return exact;
    // Starts-with match (deduplicated)
    const seen = new Set();
    return all.find(n => {
        if (seen.has(n.name)) return false;
        seen.add(n.name);
        return n.name.toLowerCase().startsWith(q);
    }) || null;
}

// Show/hide the neighborhood dropdown
function showNeighborhoodDropdown() {
    const dd = document.getElementById('neighborhood-dropdown');
    if (dd) dd.style.display = 'block';
}
function hideNeighborhoodDropdown() {
    const dd = document.getElementById('neighborhood-dropdown');
    if (dd) dd.style.display = 'none';
}

// Navigate to a neighborhood and close the dropdown
function selectNeighborhood(lat, lon, name) {
    hideNeighborhoodDropdown();
    document.getElementById('search').value = name;
    flyToNeighborhood(lat, lon, name);
}

// Render filtered neighborhood rows into the dropdown
function renderDropdownItems(items) {
    const dd = document.getElementById('neighborhood-dropdown');
    if (!dd) return;

    const medals = ['🥇', '🥈', '🥉'];

    if (items.length === 0) {
        dd.innerHTML = '<div class="dropdown-empty">No neighborhoods found</div>';
        return;
    }

    const rows = items.map(n => {
        const globalIdx = rankedNeighborhoods.indexOf(n);
        const pct = Math.max(4, Math.round((n.spots / rankingsMaxSpots) * 100));
        const rank = medals[globalIdx] ||
            `<span style="color:var(--text-muted);font-size:12px;font-weight:700;">${globalIdx + 1}</span>`;
        return `
            <div class="ranking-row" onclick="selectNeighborhood(${n.lat}, ${n.lon}, '${n.name}')">
                <div class="ranking-rank">${rank}</div>
                <div class="ranking-body">
                    <div class="ranking-header-row">
                        <span class="ranking-name">${n.name}</span>
                        <span class="ranking-spots">${n.spots.toLocaleString()} spots</span>
                    </div>
                    <div class="ranking-bar-bg">
                        <div class="ranking-bar-fill" style="width:0%" data-target="${pct}"></div>
                    </div>
                    <div class="ranking-lots">${n.lots} structure${n.lots !== 1 ? 's' : ''} detected</div>
                </div>
            </div>
        `;
    }).join('');

    const label = items.length === rankedNeighborhoods.length
        ? 'ALL NEIGHBORHOODS — RANKED BY PARKING'
        : `${items.length} MATCH${items.length !== 1 ? 'ES' : ''}`;

    dd.innerHTML = `<div class="dropdown-header">${label}</div>${rows}`;

    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            dd.querySelectorAll('.ranking-bar-fill').forEach(bar => {
                bar.style.width = bar.dataset.target + '%';
            });
        });
    });
}

// Filter dropdown rows by a search query
function filterNeighborhoodDropdown(query) {
    const q = query.toLowerCase().trim();
    const filtered = q.length === 0
        ? rankedNeighborhoods
        : rankedNeighborhoods.filter(n => n.name.toLowerCase().includes(q));
    renderDropdownItems(filtered);
}

// Compute neighborhood rankings and populate the dropdown
function buildNeighborhoodRankings() {
    if (!garageData || !garageData.features) return;

    const RADIUS = 0.015;
    const seen = new Set();
    const neighborhoods = Object.values(ATLANTA_NEIGHBORHOODS).filter(n => {
        if (seen.has(n.name)) return false;
        seen.add(n.name);
        return true;
    });

    const features = garageData.features;

    rankedNeighborhoods = neighborhoods.map(nbhd => {
        const nearby = features.filter(f => {
            const [flon, flat] = f.geometry.coordinates;
            return Math.abs(flat - nbhd.lat) < RADIUS && Math.abs(flon - nbhd.lon) < RADIUS;
        });
        const spots = nearby.reduce((sum, f) => {
            const p = f.properties;
            if (p.capacity && p.capacity > 0) return sum + p.capacity;
            if (p.levels && p.levels > 0)     return sum + p.levels * 150;
            if (p.source === 'Google Places')  return sum + 200;
            return sum + 80;
        }, 0);
        return { ...nbhd, lots: nearby.length, spots };
    }).sort((a, b) => b.spots - a.spots);

    rankingsMaxSpots = rankedNeighborhoods[0]?.spots || 1;
}

// Return density color based on how many P markers are within ~500m
function getDensityColor(lat, lon, allFeatures) {
    const R = 0.005; // ~500m in degrees
    const count = allFeatures.filter(f => {
        const [flon, flat] = f.geometry.coordinates;
        return Math.abs(flat - lat) < R && Math.abs(flon - lon) < R;
    }).length;
    if (count >= 12) return { fill: '#EF4444', border: '#B91C1C', label: 'High Density' };
    if (count >= 5)  return { fill: '#F59E0B', border: '#B45309', label: 'Medium Density' };
    return              { fill: '#22C55E', border: '#15803D', label: 'Low Density' };
}

// Build a rectangle polygon (lat/lon bounds) around a point
function makeRectPoly(lat, lon, halfDeg) {
    return [
        [lat - halfDeg, lon - halfDeg],
        [lat - halfDeg, lon + halfDeg],
        [lat + halfDeg, lon + halfDeg],
        [lat + halfDeg, lon - halfDeg]
    ];
}

// Render the polygon density view
function renderPolygonView() {
    // Clear existing polygon layer
    if (polygonLayer) {
        map.removeLayer(polygonLayer);
        polygonLayer = null;
    }
    // Hide P markers while in polygon view
    if (garageLayer) {
        map.removeLayer(garageLayer);
    }

    if (!garageData || !garageData.features) return;

    const features = garageData.features;
    const layerGroup = L.layerGroup();

    features.forEach(feat => {
        const [lon, lat] = feat.geometry.coordinates;
        const props = feat.properties;
        const isGoogle = props.source === 'Google Places';

        // Apply the same level filter as the P markers
        const levelCat = isGoogle ? 'medium' : getGarageLevelCategory(props.levels);
        if (!sizeFilters[levelCat]) return;

        // Size of rectangle: larger for taller / more capacity
        const levels = props.levels || 3;
        const capacity = props.capacity || 0;
        let halfDeg = 0.00018; // ~20m default
        if (levels >= 8 || capacity > 500) halfDeg = 0.00035;
        else if (levels >= 4 || capacity > 200) halfDeg = 0.00025;

        const { fill, border, label } = getDensityColor(lat, lon, features);
        const isGoogle2 = props.source === 'Google Places';
        const title = props.name || 'Parking Structure';
        const rating = props.rating;
        const ratingColor = rating >= 4.0 ? '#22C55E' : rating >= 3.0 ? '#F59E0B' : '#EF4444';

        const poly = L.polygon(makeRectPoly(lat, lon, halfDeg), {
            fillColor: fill,
            fillOpacity: 0.55,
            color: border,
            weight: 1.5,
            opacity: 0.9
        });

        const popupContent = `
            <div class="popup-title" style="display:flex;align-items:center;gap:6px;">
                ${isGoogle2
                    ? `<span style="background:#1A73E8;color:white;font-size:10px;font-weight:700;padding:2px 5px;border-radius:4px;">G</span>`
                    : `<span style="background:#7C3AED;color:white;font-size:10px;font-weight:700;padding:2px 5px;border-radius:4px;">P</span>`}
                ${title}
            </div>
            <div class="popup-info">
                <div style="display:inline-block;background:${fill};color:white;font-size:11px;font-weight:600;padding:2px 8px;border-radius:10px;margin-bottom:6px;">${label}</div><br>
                ${props.address ? `<div style="color:#9CA3AF;font-size:12px;margin-bottom:4px;">📍 ${props.address}</div>` : ''}
                ${props.levels ? `<strong>Floors:</strong> ${props.levels}<br>` : ''}
                ${props.capacity ? `<strong>Capacity:</strong> ${props.capacity.toLocaleString()} spaces<br>` : ''}
                ${isGoogle2 && rating ? `<strong>Rating:</strong> <span style="color:${ratingColor};">★ ${rating.toFixed(1)}</span> (${(props.total_ratings||0).toLocaleString()} reviews)<br>` : ''}
                ${props.estimated_hourly ? `<strong>Est. Rate:</strong> <span style="color:#4ECDC4;">${props.estimated_hourly}/hr</span><br>` : ''}
                <button onclick="window.open('https://www.google.com/maps/dir/?api=1&destination=${lat},${lon}','_blank')"
                    style="margin-top:10px;width:100%;padding:8px;background:${isGoogle2 ? '#1A73E8' : '#7C3AED'};border:none;border-radius:6px;color:white;font-weight:600;cursor:pointer;font-size:13px;">
                    📍 Get Directions
                </button>
            </div>
        `;
        poly.bindPopup(popupContent, { maxWidth: 300 });

        poly.on('mouseover', function() {
            this.setStyle({ fillOpacity: 0.8, weight: 2.5 });
        });
        poly.on('mouseout', function() {
            this.setStyle({ fillOpacity: 0.55, weight: 1.5 });
        });

        layerGroup.addLayer(poly);
    });

    polygonLayer = layerGroup;
    map.addLayer(polygonLayer);

    // Overlay ML model polygons on top (same style as Model view, no edit buttons)
    if (modelLayer) { map.removeLayer(modelLayer); modelLayer = null; }
    if (parkingData && parkingData.features && parkingData.features.length > 0) {
        modelLayer = L.geoJSON(parkingData.features, {
            style: (feature) => {
                const cat  = feature.properties.size_category || 'small';
                const conf = feature.properties.confidence || 0.5;
                const color = SIZE_COLORS[cat] || '#4ECDC4';
                return { fillColor: color, fillOpacity: 0.45 + conf * 0.35, color, weight: 1, opacity: 0.85 };
            },
            onEachFeature: (feature, layer) => {
                const props = feature.properties;
                const cat = props.size_category || 'small';
                const color = SIZE_COLORS[cat] || '#4ECDC4';
                const confPct = Math.round((props.confidence || 0) * 100);
                const confColor = confPct >= 80 ? '#22C55E' : confPct >= 60 ? '#F59E0B' : '#EF4444';
                layer.bindPopup(`
                    <div class="popup-title">Detected Lot #${props.lot_id ?? 'N/A'}</div>
                    <div class="popup-info">
                        <div style="display:inline-block;background:${color};color:#000;font-size:11px;font-weight:700;padding:2px 10px;border-radius:10px;margin-bottom:8px;">${cat}</div><br>
                        <strong>Est. Spots:</strong> ${scaleStat(props.num_spots)}<br>
                        <strong>Area:</strong> ${scaleStat(props.area_m2).toLocaleString()} m²<br>
                        <strong>Confidence:</strong> <span style="color:${confColor};font-weight:700;">${confPct}%</span>
                    </div>
                `, { maxWidth: 240 });
                layer.on('mouseover', function() { this.setStyle({ fillOpacity: 0.9, weight: 2 }); });
                layer.on('mouseout',  function() {
                    const c = this.feature.properties.confidence || 0.5;
                    this.setStyle({ fillOpacity: 0.45 + c * 0.35, weight: 1 });
                });
            }
        }).addTo(map);
    }
}

// Update the model toolbar counter and undo button state
function updateModelToolbar() {
    const countEl = document.getElementById('model-removed-count');
    const undoBtn = document.getElementById('model-undo-btn');
    if (countEl) countEl.textContent = `${removedLots.length} removed`;
    if (undoBtn) undoBtn.disabled = removedLots.length === 0;
}

// Remove a detected lot by lot_id (called from popup Remove button)
function removeModelLot(lotId) {
    const idx = parkingData.features.findIndex(f => f.properties.lot_id === lotId);
    if (idx === -1) return;
    removedLots.push(parkingData.features.splice(idx, 1)[0]);
    map.closePopup();
    updateModelToolbar();
    renderModelView();

    // Persist removal to disk via the backend
    fetch('http://localhost:5001/remove-lot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lot_id: lotId })
    }).catch(() => {}); // silent fail if backend is offline
}

// Restore the last removed lot
function undoLastRemoval() {
    if (removedLots.length === 0) return;
    const feat = removedLots.pop();
    // Re-insert in sorted order by lot_id
    const insertAt = parkingData.features.findIndex(
        f => f.properties.lot_id > feat.properties.lot_id
    );
    if (insertAt === -1) parkingData.features.push(feat);
    else parkingData.features.splice(insertAt, 0, feat);
    updateModelToolbar();
    renderModelView();
}

// Download the current (cleaned) parkingData as a GeoJSON file
function exportCleanedGeoJSON() {
    const json = JSON.stringify({ type: 'FeatureCollection', features: parkingData.features }, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = 'parking_lots_cleaned.geojson';
    a.click();
    URL.revokeObjectURL(url);
}

// Render the ML model segmentation output as colored polygons
function renderModelView() {
    if (modelLayer) {
        map.removeLayer(modelLayer);
        modelLayer = null;
    }

    if (!parkingData || !parkingData.features || parkingData.features.length === 0) return;

    const categoryLabels = {
        small:  'Small Lot (< 50 spots)',
        medium: 'Medium Lot (50–200 spots)',
        large:  'Large Lot (200+ spots)'
    };

    modelLayer = L.geoJSON(parkingData.features, {
        style: (feature) => {
            const cat   = feature.properties.size_category || 'small';
            const conf  = feature.properties.confidence || 0.5;
            const color = SIZE_COLORS[cat] || '#4ECDC4';
            return {
                fillColor:   color,
                fillOpacity: 0.45 + conf * 0.35,
                color:       color,
                weight:      1,
                opacity:     0.85
            };
        },
        onEachFeature: (feature, layer) => {
            const props     = feature.properties;
            const cat       = props.size_category || 'small';
            const color     = SIZE_COLORS[cat] || '#4ECDC4';
            const confPct   = Math.round((props.confidence || 0) * 100);
            const confColor = confPct >= 80 ? '#22C55E' : confPct >= 60 ? '#F59E0B' : '#EF4444';
            const lotId     = props.lot_id ?? null;

            layer.bindPopup(`
                <div class="popup-title">Detected Lot #${lotId ?? 'N/A'}</div>
                <div class="popup-info">
                    <div style="display:inline-block;background:${color};color:#000;font-size:11px;font-weight:700;padding:2px 10px;border-radius:10px;margin-bottom:8px;">
                        ${categoryLabels[cat] || cat}
                    </div><br>
                    <strong>Est. Spots:</strong> ${scaleStat(props.num_spots)}<br>
                    <strong>Area:</strong> ${scaleStat(props.area_m2).toLocaleString()} m²<br>
                    <strong>Confidence:</strong> <span style="color:${confColor};font-weight:700;">${confPct}%</span><br>
                    ${lotId !== null ? `
                    <button onclick="removeModelLot(${lotId})"
                        style="margin-top:10px;width:100%;padding:7px;background:#EF4444;border:none;border-radius:6px;color:white;font-weight:700;cursor:pointer;font-size:12px;">
                        🗑 Remove this detection
                    </button>` : ''}
                </div>
            `, { maxWidth: 260 });

            layer.on('mouseover', function() {
                this.setStyle({ fillOpacity: 0.9, weight: 2 });
            });
            layer.on('mouseout', function() {
                const c = this.feature.properties.confidence || 0.5;
                this.setStyle({ fillOpacity: 0.45 + c * 0.35, weight: 1 });
            });
        }
    });

    modelLayer.addTo(map);
}

// Switch between views
function switchView(view) {
    currentView = view;

    // Update button states
    document.querySelectorAll('.view-toggle-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === view);
    });

    // Clear layers belonging to views we're leaving
    if (view !== 'polygons' && polygonLayer) {
        map.removeLayer(polygonLayer);
        polygonLayer = null;
    }
    if (view !== 'polygons' && modelLayer) {
        map.removeLayer(modelLayer);
        modelLayer = null;
    }

    // Show/hide appropriate content
    const mapEl = document.getElementById('map');
    const analyticsEl = document.getElementById('analytics-dashboard');

    if (view === 'map') {
        mapEl.style.display = 'block';
        analyticsEl.style.display = 'none';
        renderParkingLots();
        renderGarages();
    } else if (view === 'polygons') {
        mapEl.style.display = 'block';
        analyticsEl.style.display = 'none';
        renderPolygonView();
    } else if (view === 'analytics') {
        mapEl.style.display = 'none';
        analyticsEl.style.display = 'block';
        renderGarages();
        createAnalyticsCharts();
    }
}

// Create analytics charts — ML model + garage data
function createAnalyticsCharts() {
    // Destroy existing charts
    Object.values(charts).forEach(chart => chart.destroy());
    charts = {};

    const gFeatures = (garageData && garageData.features) ? garageData.features : [];
    const mFeatures = (parkingData && parkingData.features) ? parkingData.features : [];

    const chartOpts = {
        responsive: true,
        maintainAspectRatio: true,
        plugins: { legend: { labels: { color: '#E5E7EB' } } }
    };
    const axisOpts = {
        y: { beginAtZero: true, ticks: { color: '#9CA3AF' }, grid: { color: '#2D3348' } },
        x: { ticks: { color: '#9CA3AF' }, grid: { color: '#2D3348' } }
    };

    // 1. Neighborhood Parking Density — top 8 by estimated spots from ML model
    const hoodSpots = {};
    Object.entries(ATLANTA_NEIGHBORHOODS).forEach(([key, hood]) => {
        const spots = mFeatures.filter(f => {
            const coords = f.geometry && f.geometry.coordinates;
            if (!coords) return false;
            // centroid of polygon ring
            const ring = f.geometry.type === 'Polygon' ? coords[0] : coords[0][0];
            const avgLat = ring.reduce((s, c) => s + c[1], 0) / ring.length;
            const avgLon = ring.reduce((s, c) => s + c[0], 0) / ring.length;
            return Math.abs(avgLat - hood.lat) < 0.018 && Math.abs(avgLon - hood.lon) < 0.018;
        }).reduce((s, f) => s + scaleStat(f.properties.num_spots), 0);
        if (spots > 0) hoodSpots[hood.name] = spots;
    });
    const top8 = Object.entries(hoodSpots).sort((a, b) => b[1] - a[1]).slice(0, 8);

    charts.neighborhoodChart = new Chart(document.getElementById('neighborhoodChart'), {
        type: 'bar',
        data: {
            labels: top8.map(e => e[0]),
            datasets: [{
                label: 'Est. Spots',
                data: top8.map(e => e[1]),
                backgroundColor: '#1A73E8',
                borderRadius: 4,
                borderWidth: 0
            }]
        },
        options: {
            ...chartOpts,
            indexAxis: 'y',
            scales: {
                y: { ticks: { color: '#E5E7EB' }, grid: { color: '#2D3348' } },
                x: { beginAtZero: true, ticks: { color: '#9CA3AF' }, grid: { color: '#2D3348' } }
            }
        }
    });

    // 2. Model Confidence Distribution — 10 buckets 0–100%
    const confBuckets = Array(10).fill(0);
    mFeatures.forEach(f => {
        const idx = Math.min(9, Math.floor((f.properties.confidence || 0) * 10));
        confBuckets[idx]++;
    });
    const confLabels = ['0–10%','10–20%','20–30%','30–40%','40–50%','50–60%','60–70%','70–80%','80–90%','90–100%'];
    const confColors = confLabels.map((_, i) => {
        const t = i / 9;
        const r = Math.round(239 - t * (239 - 34));
        const g = Math.round(68  + t * (197 - 68));
        const b = Math.round(68  + t * (94  - 68));
        return `rgb(${r},${g},${b})`;
    });

    charts.confidenceChart = new Chart(document.getElementById('confidenceChart'), {
        type: 'bar',
        data: {
            labels: confLabels,
            datasets: [{
                label: 'Lots',
                data: confBuckets,
                backgroundColor: confColors,
                borderWidth: 0,
                borderRadius: 3
            }]
        },
        options: { ...chartOpts, scales: axisOpts }
    });

    // 3. Detected Lot Size Breakdown — donut
    const small  = mFeatures.filter(f => f.properties.size_category === 'small').length;
    const medium = mFeatures.filter(f => f.properties.size_category === 'medium').length;
    const large  = mFeatures.filter(f => f.properties.size_category === 'large').length;

    charts.sizeChart = new Chart(document.getElementById('sizeChart'), {
        type: 'doughnut',
        data: {
            labels: [`Small <50 (${small})`, `Medium 50–200 (${medium})`, `Large 200+ (${large})`],
            datasets: [{
                data: [small, medium, large],
                backgroundColor: ['#4ECDC4', '#FFB84D', '#E74C3C'],
                borderColor: '#1A1F3A',
                borderWidth: 2
            }]
        },
        options: { ...chartOpts }
    });

}

// Setup event listeners
function setupEventListeners() {
    // View toggle buttons
    document.querySelectorAll('.view-toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            switchView(btn.dataset.view);
        });
    });

    // Size filter buttons
    document.querySelectorAll('.size-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const size = btn.dataset.size;
            sizeFilters[size] = !sizeFilters[size];

            // Toggle active class
            btn.classList.toggle('active');

            // Apply filters
            applyFilters();
        });
    });

    // Confidence slider
    const confidenceSlider = document.getElementById('min-confidence');
    const confidenceValue = document.getElementById('min-confidence-value');

    confidenceSlider.addEventListener('input', (e) => {
        minConfidence = parseInt(e.target.value);
        confidenceValue.textContent = minConfidence + '%';
        applyFilters();
    });

    // Search input — filter lots + neighborhood dropdown
    const searchInput = document.getElementById('search');
    searchInput.addEventListener('focus', () => {
        filterNeighborhoodDropdown(searchInput.value);
        showNeighborhoodDropdown();
    });
    searchInput.addEventListener('input', (e) => {
        searchQuery = e.target.value;
        applyFilters();
        filterNeighborhoodDropdown(e.target.value);
        showNeighborhoodDropdown();
    });
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            const match = findNeighborhoodMatch(searchInput.value);
            if (match) selectNeighborhood(match.lat, match.lon, match.name);
            else hideNeighborhoodDropdown();
        } else if (e.key === 'Escape') {
            hideNeighborhoodDropdown();
            searchInput.blur();
        }
    });
    // Close dropdown on outside click
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-container')) {
            hideNeighborhoodDropdown();
        }
    });

    // Garage toggle
    const garageToggle = document.getElementById('show-garages');
    if (garageToggle) {
        garageToggle.addEventListener('change', (e) => {
            showGarages = e.target.checked;
            renderGarages();
        });
    }

    // Street parking toggle
    const streetParkingToggle = document.getElementById('show-street-parking');
    if (streetParkingToggle) {
        streetParkingToggle.addEventListener('change', (e) => {
            showStreetParking = e.target.checked;
            renderStreetParking();
        });
    }

    // Chatbot toggle
    const chatbotToggle = document.getElementById('chatbot-toggle');
    const chatbotPanel = document.getElementById('chatbot-panel');
    const chatbotClose = document.getElementById('chatbot-close');

    if (chatbotToggle && chatbotPanel) {
        chatbotToggle.addEventListener('click', () => {
            chatbotPanel.classList.add('open');
            chatbotToggle.style.display = 'none';
        });

        chatbotClose.addEventListener('click', () => {
            chatbotPanel.classList.remove('open');
            chatbotToggle.style.display = 'flex';
        });
    }

    // Chatbot send message
    const chatbotInput = document.getElementById('chatbot-input');
    const chatbotSend = document.getElementById('chatbot-send');

    if (chatbotSend && chatbotInput) {
        chatbotSend.addEventListener('click', () => {
            sendChatMessage();
        });

        chatbotInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendChatMessage();
            }
        });
    }

    // Suggestion buttons
    document.querySelectorAll('.suggestion-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const query = btn.dataset.query;
            chatbotInput.value = query;
            sendChatMessage();
        });
    });
}

// Send chat message
// Old chatbot functions removed - now using chatbot.js with RAG API

// Show error message
function showErrorMessage(message) {
    const errorDiv = document.createElement('div');
    errorDiv.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: #1A1F3A;
        border: 1px solid #E74C3C;
        border-radius: 8px;
        padding: 24px;
        color: #E5E7EB;
        z-index: 10000;
        max-width: 400px;
        text-align: center;
    `;

    errorDiv.innerHTML = `
        <h3 style="color: #E74C3C; margin-bottom: 12px;">Data Not Found</h3>
        <p style="color: #9CA3AF; font-size: 14px;">${message}</p>
        <p style="color: #9CA3AF; font-size: 12px; margin-top: 12px;">
            Run the pipeline:
            <code style="background: #0A0E27; padding: 2px 6px; border-radius: 3px; display: block; margin-top: 8px;">
                python scripts/01_train_model.py<br>
                python scripts/02_download_naip.py<br>
                python scripts/03_run_inference.py<br>
                python scripts/04_generate_geojson.py
            </code>
        </p>
    `;

    document.body.appendChild(errorDiv);
}

// Highlight recommended neighborhood on map
function highlightNeighborhood(neighborhoodName, businessType) {
    // Normalize neighborhood name for lookup
    const normalizedName = neighborhoodName.toLowerCase().trim();

    // Check if we have coordinates for this neighborhood
    const neighborhood = ATLANTA_NEIGHBORHOODS[normalizedName];

    if (!neighborhood) {
        console.log('Unknown neighborhood:', neighborhoodName);
        return;
    }

    // Check if already marked
    const existingMarker = recommendationData.find(r => r.neighborhood === normalizedName);
    if (existingMarker) {
        console.log('Neighborhood already marked:', neighborhoodName);
        return;
    }

    // Create circular highlight area (approx 1km radius)
    const circle = L.circle([neighborhood.lat, neighborhood.lon], {
        color: '#9B59B6',
        fillColor: '#9B59B6',
        fillOpacity: 0.15,
        weight: 3,
        radius: 1000 // meters
    }).addTo(map);

    // Create marker
    const marker = L.marker([neighborhood.lat, neighborhood.lon], {
        icon: L.divIcon({
            html: `<div style="background: #9B59B6; width: 30px; height: 30px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 15px rgba(155, 89, 182, 0.8); display: flex; align-items: center; justify-content: center; font-size: 16px;">🎯</div>`,
            className: 'recommendation-marker',
            iconSize: [30, 30],
            iconAnchor: [15, 15]
        })
    }).addTo(map);

    // Create popup
    const popupContent = `
        <div class="popup-title">🎯 Recommended: ${neighborhood.name}</div>
        <div class="popup-content">
            ${businessType ? `<p><strong>For:</strong> ${businessType}</p>` : ''}
            <p style="color: #9B59B6; font-weight: 500; margin-top: 8px;">Business Advisor Recommendation</p>
        </div>
    `;

    marker.bindPopup(popupContent);

    // Store marker and circle
    recommendationMarkers.push(marker);
    recommendationMarkers.push(circle);
    recommendationData.push({
        neighborhood: normalizedName,
        businessType: businessType
    });

    console.log('Highlighted neighborhood:', neighborhood.name, 'for', businessType);

    // Pan to show the recommendation (if not too far from current view)
    const currentBounds = map.getBounds();
    const markerLatLng = L.latLng(neighborhood.lat, neighborhood.lon);

    if (!currentBounds.contains(markerLatLng)) {
        map.setView(markerLatLng, 13, { animate: true });
    }
}

// Clear all recommendation markers
function clearRecommendations() {
    // Remove all markers and circles from map
    recommendationMarkers.forEach(marker => {
        map.removeLayer(marker);
    });

    // Clear arrays
    recommendationMarkers = [];
    recommendationData = [];

    console.log('Cleared all recommendation markers');
}

// Parse chatbot response and highlight neighborhoods
function processChatbotRecommendation(response, businessType = null) {
    // Extract neighborhood names from response
    const responseText = response.toLowerCase();

    // Check each neighborhood
    for (const [key, data] of Object.entries(ATLANTA_NEIGHBORHOODS)) {
        // Check if neighborhood name appears in response
        // Match variations like "**Midtown**", "Midtown", "midtown", etc.
        const escapedName = data.name.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`\\*\\*${escapedName}\\*\\*|\\b${escapedName}\\b`, 'i');

        if (regex.test(responseText)) {
            highlightNeighborhood(data.name, businessType);
        }
    }
}

// Initialize app
function init() {
    console.log('Initializing ParkSight...');

    // Initialize map
    initMap();

    // Setup event listeners
    setupEventListeners();

    // Load parking data
    loadParkingData();

    // Load garage data
    loadGarageData();

    // Load street parking data
    loadStreetParkingData();

    console.log('ParkSight initialized');
}

// Run on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
