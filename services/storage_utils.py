import tarfile, os, subprocess
def archive_and_upload(frames_dir, out_archive, bucket, key):
    with tarfile.open(out_archive, "w:gz") as tar:
        tar.add(frames_dir, arcname="frames")
    upload_to_s3.delay(out_archive, bucket, key)
