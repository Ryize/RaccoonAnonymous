from flask import Flask

app = Flask(__name__)

if __name__ == '__main__':
    from controller import app
    app.run(debug=True, host='0.0.0.0', port=5001)
