from flask import Flask, render_template, request
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        manga_url = request.form.get('manga_url')
        format_choice = request.form.get('format_choice')
        # We'll add the processing logic later
        return render_template('index.html', 
                                message=f"Processing {manga_url} in {format_choice} format...")
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True) 