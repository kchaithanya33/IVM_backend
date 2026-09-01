import logging
import azure.functions as func
import io


def main(req: func.HttpRequest) -> func.HttpResponse:
    """Test endpoint to download Excel directly for debugging"""

    try:
        # Sample test data
        test_data = {
            "failedAssetsWindows": [
                {
                    "ip": "192.168.1.1",
                    "hostname": "server1",
                    "osType": "Windows Server 2019",
                    "failureReason": "Auth failed",
                    "tech": "SMB"
                },
                {
                    "ip": "192.168.1.2",
                    "hostname": "server2",
                    "osType": "Windows Server 2022",
                    "failureReason": "Incorrect credentials",
                    "tech": "WMI"
                }
            ],
            "failedAssetsUnix": [
                {
                    "ip": "10.0.0.1",
                    "hostname": "linux-srv1",
                    "osType": "Ubuntu 20.04",
                    "failureReason": "Permission denied",
                    "tech": "SSH"
                }
            ],
            "notAliveAssetsWindows": [
                "192.168.2.1",
                "192.168.2.2"
            ],
            "notAliveAssetsUnix": [
                "10.0.0.5"
            ],
            "notAliveAssetsUnknown": [
                "172.16.0.1"
            ]
        }

        # Generate Excel
        authfail_wb = create_authfail_excel(
            test_data
        )

        buffer = io.BytesIO()

        authfail_wb.save(buffer)

        buffer.seek(0)

        return func.HttpResponse(
            buffer.getvalue(),
            status_code=200,
            mimetype=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition":
                    "attachment; "
                    "filename=test_authfail.xlsx"
            }
        )

    except Exception as e:

        logging.error(
            f"Error in test download: {str(e)}"
        )

        return func.HttpResponse(
            f"Error: {str(e)}",
            status_code=500
        )