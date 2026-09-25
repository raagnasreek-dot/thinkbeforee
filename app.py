from flask import Flask, request, jsonify, send_from_directory, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash


# =====================================================
# FLASK APP
# =====================================================

app = Flask(__name__)

# Secret key for login sessions
app.secret_key = "thinkbefore-local-secret-key"


# =====================================================
# MYSQL CONNECTION
# =====================================================

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="thinkbefore"
)

print("MySQL Database Connected Successfully!")


# =====================================================
# HOME PAGE
# =====================================================

@app.route("/")
def home():
    return send_from_directory(".", "index.html")


# =====================================================
# REGISTER
# =====================================================

@app.route("/register", methods=["POST"])
def register():

    try:

        data = request.get_json()

        name = data.get("name")
        email = data.get("email")
        password = data.get("password")

        # Check empty fields
        if not name or not email or not password:

            return jsonify({
                "error": "All fields are required."
            }), 400

        cursor = db.cursor()

        # Check whether email already exists
        cursor.execute(
            """
            SELECT user_id
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            cursor.close()

            return jsonify({
                "error": "Email already registered."
            }), 409

        # Hash password before storing
        hashed_password = generate_password_hash(password)

        # Insert user
        cursor.execute(
            """
            INSERT INTO users
            (name, email, password)
            VALUES (%s, %s, %s)
            """,
            (
                name,
                email,
                hashed_password
            )
        )

        db.commit()
        cursor.close()

        return jsonify({
            "message": "Registration successful!"
        })

    except Exception as e:

        print("REGISTER ERROR:", e)

        return jsonify({
            "error": "Registration failed."
        }), 500


# =====================================================
# LOGIN
# =====================================================

@app.route("/login", methods=["POST"])
def login():

    try:

        data = request.get_json()

        email = data.get("email")
        password = data.get("password")

        # Check empty fields
        if not email or not password:

            return jsonify({
                "error": "Email and password are required."
            }), 400

        cursor = db.cursor(dictionary=True)

        # Find user
        cursor.execute(
            """
            SELECT
                user_id,
                name,
                email,
                password
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()

        # User does not exist
        if not user:

            return jsonify({
                "error": "Invalid email or password."
            }), 401

        stored_password = user["password"]

        # =================================================
        # CHECK PASSWORD
        # =================================================

        password_correct = False

        # First try hashed password
        try:

            password_correct = check_password_hash(
                stored_password,
                password
            )

        except Exception:

            password_correct = False

        # =================================================
        # OLD PLAIN TEXT PASSWORD SUPPORT
        # =================================================

        if not password_correct and stored_password == password:

            print("Old plain-text password detected.")

            new_password = generate_password_hash(password)

            cursor = db.cursor()

            cursor.execute(
                """
                UPDATE users
                SET password = %s
                WHERE user_id = %s
                """,
                (
                    new_password,
                    user["user_id"]
                )
            )

            db.commit()
            cursor.close()

            password_correct = True

        # Wrong password
        if not password_correct:

            return jsonify({
                "error": "Invalid email or password."
            }), 401

        # =================================================
        # CREATE LOGIN SESSION
        # =================================================

        session["user_id"] = user["user_id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]

        print(
            "LOGIN SUCCESS:",
            user["user_id"],
            user["email"]
        )

        return jsonify({

            "message": "Login successful!",

            "user": {

                "user_id": user["user_id"],
                "name": user["name"],
                "email": user["email"]

            }

        })

    except Exception as e:

        print("LOGIN ERROR:", e)

        return jsonify({
            "error": "Login failed."
        }), 500


# =====================================================
# CHECK CURRENT USER
# =====================================================

@app.route("/me", methods=["GET"])
def current_user():

    if "user_id" not in session:

        return jsonify({
            "logged_in": False
        })

    return jsonify({

        "logged_in": True,

        "user": {

            "user_id": session["user_id"],
            "name": session["user_name"],
            "email": session["user_email"]

        }

    })


# =====================================================
# LOGOUT
# =====================================================

@app.route("/logout", methods=["POST"])
def logout():

    session.clear()

    return jsonify({
        "message": "Logged out successfully."
    })


# =====================================================
# TEMPORARY AI DECISION ANALYSIS
# =====================================================

@app.route("/analyze", methods=["POST"])
def analyze():

    try:

        # User must be logged in
        if "user_id" not in session:

            return jsonify({
                "error": "Please login first."
            }), 401

        data = request.get_json()

        decision_text = data.get(
            "decision_text",
            ""
        )

        category = data.get(
            "category",
            ""
        )

        if not decision_text:

            return jsonify({
                "error": "Please enter a decision."
            }), 400

        # =================================================
        # TEMPORARY MOCK AI RESPONSE
        # =================================================

        result = {

            "risk": "Medium",

            "concerns": [

                "The situation may involve some risk.",

                "The available information may not be enough to verify whether it is safe.",

                "There could be unexpected consequences if you proceed without checking."

            ],

            "verify": [

                "Verify the source or person involved.",

                "Check whether the information is genuine.",

                "Look for trusted information before proceeding."

            ],

            "saferAlternative":
                "Take some time to verify the details before making the decision.",

            "why":
                "The decision needs more information before its risk can be judged confidently."

        }

        print(
            "TEMPORARY AI ANALYSIS SUCCESS"
        )

        return jsonify(result)

    except Exception as e:

        print(
            "ANALYZE ERROR:",
            e
        )

        return jsonify({
            "error": "Analysis failed."
        }), 500


# =====================================================
# SAVE DECISION
# =====================================================

@app.route("/save-decision", methods=["POST"])
def save_decision():

    try:

        # User must be logged in
        if "user_id" not in session:

            return jsonify({
                "error": "Please login first."
            }), 401

        data = request.get_json()

        decision_text = data.get(
            "decision_text"
        )

        category = data.get(
            "category"
        )

        risk_level = data.get(
            "risk_level"
        )

        concerns = data.get(
            "concerns"
        )

        safer_alternative = data.get(
            "safer_alternative"
        )

        cursor = db.cursor()

        query = """
            INSERT INTO decisions
            (
                user_id,
                decision_text,
                category,
                risk_level,
                concerns,
                safer_alternative
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
        """

        values = (

            session["user_id"],

            decision_text,

            category,

            risk_level,

            concerns,

            safer_alternative

        )

        cursor.execute(
            query,
            values
        )

        db.commit()
        cursor.close()

        print(
            "DECISION SAVED FOR USER:",
            session["user_id"]
        )

        return jsonify({
            "message": "Decision saved successfully!"
        })

    except Exception as e:

        print(
            "MYSQL SAVE ERROR:",
            e
        )

        return jsonify({
            "error": "Could not save decision."
        }), 500


# =====================================================
# GET ALL DECISION HISTORY
# =====================================================

@app.route("/decisions", methods=["GET"])
def get_decisions():

    try:

        # User must be logged in
        if "user_id" not in session:

            return jsonify({
                "error": "Please login first."
            }), 401

        cursor = db.cursor(
            dictionary=True
        )

        # =================================================
        # GET ALL SAVED DECISIONS FROM MYSQL
        #
        # IMPORTANT:
        # No UPDATE
        # No DELETE
        # No changes to existing records
        # =================================================

        cursor.execute(
            """
            SELECT
                decision_id,
                user_id,
                decision_text,
                category,
                risk_level,
                concerns,
                safer_alternative,
                created_at
            FROM decisions
            ORDER BY created_at DESC
            """
        )

        decisions = cursor.fetchall()

        cursor.close()

        print(
            "HISTORY LOADED:",
            len(decisions),
            "decisions"
        )

        return jsonify(decisions)

    except Exception as e:

        print(
            "MYSQL HISTORY ERROR:",
            e
        )

        return jsonify({
            "error": "Could not load decision history."
        }), 500


# =====================================================
# RUN FLASK SERVER
# =====================================================

if __name__ == "__main__":

    print("Starting ThinkBefore...")

    app.run(
        debug=True
    )