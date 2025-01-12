const socket = io();
const gallery = document.querySelector('#gallery');

// Initialize the gallery with the title if it's not already there
if (!gallery.querySelector('h1')) {
    const title = document.createElement('h1');
    title.textContent = 'Live Image Gallery';
    gallery.appendChild(title);
}

// Function to fetch all images in the /static/uploads/ directory
function fetchAllImages() {
    fetch('/get-images')
        .then(response => response.json())
        .then(images => {
            // Display all images initially
            images.forEach(image => {
                const img = document.createElement('img');
                img.src = `/static/uploads/${image}`;
                img.alt = image;
                img.style = "max-width: 400px; margin: 10px;";
                gallery.appendChild(img);
            });
        })
        .catch(err => console.error('Error fetching images:', err));
}

// Call the function to load all images on page load
fetchAllImages();

// When a new image is received via socket.io
socket.on('new_image', (data) => {
    // Create the new image element
    const img = document.createElement('img');
    img.src = `/static/uploads/${data.filename}`;
    img.alt = data.filename;
    img.style = "max-width: 400px; margin: 10px;";

    // Append the new image to the gallery
    gallery.appendChild(img);
});
