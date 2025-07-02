from flask import Flask, request, render_template
import io
import base64
from gamma_utils import process_index_data

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    imagem_base64 = None
    error_msg = None

    if request.method == 'POST':
        index_code = request.form['index']
        try:
            fig = process_index_data(index_code)
            img = io.BytesIO()
            fig.savefig(img, format='png')
            img.seek(0)
            imagem_base64 = base64.b64encode(img.read()).decode('utf8')
        except Exception as e:
            error_msg = str(e)

    return render_template('index.html', imagem=imagem_base64, erro=error_msg)

if __name__ == '__main__':
    app.run(debug=True)
