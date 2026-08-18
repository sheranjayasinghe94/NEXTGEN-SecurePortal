using System.Net.Http;
using System.Text;
using System.Text.Json;

namespace DesktopTokenGenerator;

public class ApiService
{
    private readonly HttpClient _client;
    private readonly string _baseUrl;

    public ApiService(string baseUrl)
    {
        _baseUrl = baseUrl.TrimEnd('/');
        _client = new HttpClient();
        _client.Timeout = TimeSpan.FromSeconds(15);
    }

    public async Task<TokenResponse> GenerateTokenAsync(string authFlowId, string otp, string userId, string deviceId)
    {
        var payload = new
        {
            auth_flow_id = authFlowId.Trim(),
            otp = otp.Trim(),
            user_id = userId.Trim(),
            device_id = deviceId.Trim()
        };

        var json = JsonSerializer.Serialize(payload);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        try
        {
            var response = await _client.PostAsync($"{_baseUrl}/api/generate-token/", content);
            var responseBody = await response.Content.ReadAsStringAsync();

            var result = JsonSerializer.Deserialize<TokenResponse>(responseBody, new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true
            });

            return result ?? new TokenResponse { Success = false, Error = "Empty response from server." };
        }
        catch (HttpRequestException ex) when (ex.InnerException is System.Net.Sockets.SocketException)
        {
            return new TokenResponse
            {
                Success = false,
                Error = "Cannot connect to SecurePortal server.\n\nPlease check:\n• Your internet connection is active.\n• The SecurePortal server is running.\n• The server URL is correct in settings."
            };
        }
        catch (TaskCanceledException)
        {
            return new TokenResponse
            {
                Success = false,
                Error = "Connection timed out. The server did not respond within 15 seconds."
            };
        }
        catch (Exception ex)
        {
            return new TokenResponse
            {
                Success = false,
                Error = $"Unexpected error: {ex.Message}"
            };
        }
    }
    public async Task<RegistrationResponse> RegisterDeviceAsync(string username, string registrationCode, string deviceId, string machineGuid, string deviceName, string windowsUsername, string macAddressHash)
    {
        var payload = new
        {
            username = username.Trim(),
            registration_code = registrationCode.Trim(),
            device_id = deviceId.Trim(),
            machine_guid = machineGuid.Trim(),
            device_name = deviceName.Trim(),
            windows_username = windowsUsername.Trim(),
            mac_address_hash = macAddressHash.Trim()
        };

        var json = JsonSerializer.Serialize(payload);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        try
        {
            var response = await _client.PostAsync($"{_baseUrl}/api/register-device/", content);
            var responseBody = await response.Content.ReadAsStringAsync();

            var result = JsonSerializer.Deserialize<RegistrationResponse>(responseBody, new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true
            });

            return result ?? new RegistrationResponse { Success = false, Error = "Empty response from server." };
        }
        catch (Exception ex)
        {
            return new RegistrationResponse { Success = false, Error = $"Unexpected error: {ex.Message}" };
        }
    }
}

public class RegistrationResponse
{
    public bool Success { get; set; }
    public string? Error { get; set; }
    public string? Message { get; set; }
}

public class TokenResponse
{
    public bool Success { get; set; }
    public string? Token { get; set; }
    public string? Error { get; set; }
    public string? Message { get; set; }
    public int? ExpiresInSeconds { get; set; }
    public int? LockedSeconds { get; set; }
}
