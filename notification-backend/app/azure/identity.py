from azure.identity import DefaultAzureCredential


def get_azure_credential():
    """
    Return DefaultAzureCredential.

    Local development:
        Azure CLI / Visual Studio Code / environment credentials

    Azure deployment:
        Managed Identity / Workload Identity / environment credentials
    """

    return DefaultAzureCredential(
        exclude_interactive_browser_credential=False
    )