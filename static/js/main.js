// StudySpace JavaScript Helper Functions

document.addEventListener('DOMContentLoaded', () => {
    // 1. Set minimum date for booking input to today
    const dateInput = document.getElementById('booking_date');
    if (dateInput) {
        const today = new Date();
        const year = today.getFullYear();
        const month = String(today.getMonth() + 1).padStart(2, '0');
        const day = String(today.getDate()).padStart(2, '0');
        const minDate = `${year}-${month}-${day}`;
        dateInput.setAttribute('min', minDate);
        
        // If there's no value set, default to today
        if (!dateInput.value) {
            dateInput.value = minDate;
        }
    }

    // 2. Validate booking time range on submission
    const bookingForm = document.getElementById('booking-form');
    if (bookingForm) {
        bookingForm.addEventListener('submit', (e) => {
            const startTimeInput = document.getElementById('start_time');
            const endTimeInput = document.getElementById('end_time');
            
            if (startTimeInput && endTimeInput) {
                const startVal = startTimeInput.value;
                const endVal = endTimeInput.value;
                
                if (startVal >= endVal) {
                    e.preventDefault();
                    alert('Error: End time must be after start time.');
                    return false;
                }
            }
        });
    }

    // 3. Tab switching logic (used in admin dashboard & management pages)
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabTarget = button.getAttribute('data-tab');
            
            // Remove active classes
            tabButtons.forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            // Add active class to clicked button
            button.classList.add('active');
            
            // Show corresponding content
            const targetContent = document.getElementById(tabTarget);
            if (targetContent) {
                targetContent.classList.add('active');
            }
        });
    });

    // 4. Confirmation dialogs for key actions
    const deleteButtons = document.querySelectorAll('.confirm-delete');
    deleteButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            if (!confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });

    const cancelBookingButtons = document.querySelectorAll('.confirm-cancel');
    cancelBookingButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            if (!confirm('Are you sure you want to cancel this classroom booking?')) {
                e.preventDefault();
            }
        });
    });
});

// Helper function to dynamically check classroom availability
function checkLiveAvailability(roomId, date, start, end) {
    if (!roomId || !date || !start || !end) return;
    
    // We can do a fetch request to check availability live without submitting
    fetch(`/api/check-availability?room_id=${roomId}&date=${date}&start_time=${start}&end_time=${end}`)
        .then(response => response.json())
        .then(data => {
            const indicator = document.getElementById('availability-status-indicator');
            if (indicator) {
                if (data.available) {
                    indicator.className = 'alert alert-success';
                    indicator.innerHTML = '✔ Room is available during these hours!';
                } else {
                    indicator.className = 'alert alert-danger';
                    indicator.innerHTML = `✘ Room is unavailable! Suggested Room: <strong>${data.suggestion.room_number}</strong> (${data.suggestion.building})`;
                }
            }
        })
        .catch(err => console.error("Error checking live availability:", err));
}
