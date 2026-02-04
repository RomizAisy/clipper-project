from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField, URLField
from wtforms.validators import InputRequired, URL, Optional


class ClipperFileForm(FlaskForm):
    file = FileField("File" , validators=[Optional()])
    video_url  = URLField(
        "Video URL",
        validators=[Optional(), URL()],
        render_kw={"placeholder": "Paste YouTube / TikTok link"}
    )
    submit = SubmitField("Upload File")