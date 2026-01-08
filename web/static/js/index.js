document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    const input = document.getElementById('recipe_url');

    form.addEventListener('submit', function(event) {
        let url = input.value.trim();

        // If URL doesn't start with http:// or https://, add https://
        if (url && !url.match(/^https?:\/\//i)) {
            input.value = 'https://' + url;
        }
    });
});
