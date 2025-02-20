### How to run local server
1. python -m venv venv
2. source venv/Scripts/activate (window)
3. pip install -r requirements.txt 
4. uvicorn main:app --reload

# If you are in mobile, fe team: 
- DO NOT do anything about code in be or run "python init_db.py" => it will make the DB crash
# If you are in be team:
- Check out from branch "main" and coding