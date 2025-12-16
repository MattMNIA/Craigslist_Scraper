import pytest
from bs4 import BeautifulSoup
from scraper import parse_details

SAMPLE_DETAIL_HTML = """
<!DOCTYPE html>
<html>
<body>
    <section id="postingbody">
        <div class="print-qrcode-label">QR Code Link to This Post</div>
        This is a great item.
        <br>
        It works perfectly.
    </section>
    <div class="attrgroup">
        <span>condition: good</span>
        <span>make: sony</span>
    </div>
    <div id="thumbs">
        <a href="image1.jpg" class="thumb"></a>
        <a href="image2.jpg" class="thumb"></a>
    </div>
</body>
</html>
"""

def test_parse_details():
    soup = BeautifulSoup(SAMPLE_DETAIL_HTML, "html.parser")
    details = parse_details(soup)
    
    assert "description" in details
    assert "This is a great item." in details["description"]
    assert "QR Code" not in details["description"]
    
    assert "attributes" in details
    assert "condition: good" in details["attributes"]
    assert "make: sony" in details["attributes"]
    
    assert "images" in details
    assert len(details["images"]) == 2
    assert "image1.jpg" in details["images"]
